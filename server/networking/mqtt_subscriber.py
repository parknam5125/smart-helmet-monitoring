"""MQTT ingestion that runs CBR, persists logs, and pushes WebSocket events."""

from __future__ import annotations

import asyncio
import json
import logging

import paho.mqtt.client as mqtt

from server.cbr.cbr_engine import CBREngine
from server.database.db_manager import DatabaseManager
from server.networking.connection_manager import ConnectionManager
from shared.config import Settings
from shared.constants import TOPIC_ALL_TELEMETRY, TOPIC_RISK, topic_for
from shared.models import MonitoringPayload


LOGGER = logging.getLogger(__name__)


class MQTTSubscriber:
    def __init__(
        self,
        settings: Settings,
        db: DatabaseManager,
        cbr: CBREngine,
        connection_manager: ConnectionManager,
        loop: asyncio.AbstractEventLoop,
    ) -> None:
        self.settings = settings
        self.db = db
        self.cbr = cbr
        self.connection_manager = connection_manager
        self.loop = loop
        self.client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2,
            client_id="safety-server-subscriber",
        )
        if settings.mqtt.username:
            self.client.username_pw_set(settings.mqtt.username, settings.mqtt.password)
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message

    def start(self) -> None:
        self.client.reconnect_delay_set(min_delay=1, max_delay=30)
        self.client.connect_async(
            self.settings.mqtt.host,
            self.settings.mqtt.port,
            self.settings.mqtt.keepalive_seconds,
        )
        self.client.loop_start()
        LOGGER.info(
            "MQTT 브로커에 연결을 시도합니다: %s:%s",
            self.settings.mqtt.host,
            self.settings.mqtt.port,
        )

    def stop(self) -> None:
        self.client.loop_stop()
        self.client.disconnect()

    def _on_connect(
        self,
        client: mqtt.Client,
        _userdata: object,
        _flags: mqtt.ConnectFlags,
        reason_code: mqtt.ReasonCode,
        _properties: mqtt.Properties | None,
    ) -> None:
        if reason_code == 0:
            client.subscribe(TOPIC_ALL_TELEMETRY, qos=self.settings.mqtt.qos)
            LOGGER.info("라즈베리파이 데이터 수신 대기 중: %s", TOPIC_ALL_TELEMETRY)
        else:
            LOGGER.error("MQTT 연결 실패: %s", reason_code)

    def _on_message(
        self,
        client: mqtt.Client,
        _userdata: object,
        message: mqtt.MQTTMessage,
    ) -> None:
        try:
            raw = message.payload.decode("utf-8")
            payload = MonitoringPayload.from_dict(json.loads(raw))
            assessment = self.cbr.assess(payload)
            row_id = self.db.insert_monitoring_result(payload, assessment)
            event = {
                "type": "monitoring_update",
                "log_id": row_id,
                "payload": payload.to_dict(),
                "assessment": assessment.to_dict(),
            }
            client.publish(
                topic_for(TOPIC_RISK, payload.device_id),
                json.dumps(assessment.to_dict(), separators=(",", ":")),
                qos=self.settings.mqtt.qos,
            )
            asyncio.run_coroutine_threadsafe(
                self.connection_manager.publish(payload.device_id, event),
                self.loop,
            )
        except Exception:
            LOGGER.exception("MQTT 메시지 처리 중 오류가 발생했습니다: %s", message.topic)
