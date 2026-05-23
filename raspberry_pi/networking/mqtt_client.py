"""MQTT publisher for telemetry, heartbeat, and risk command topics."""

from __future__ import annotations

import json
import logging

import paho.mqtt.client as mqtt

from shared.config import MQTTConfig
from shared.constants import TOPIC_HEARTBEAT, TOPIC_TELEMETRY, topic_for
from shared.models import MonitoringPayload, utc_now_iso


LOGGER = logging.getLogger(__name__)


class MQTTPublisher:
    def __init__(self, config: MQTTConfig, device_id: str) -> None:
        self.config = config
        self.device_id = device_id
        self.client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2,
            client_id=f"{device_id}-publisher",
        )
        if config.username:
            self.client.username_pw_set(config.username, config.password)

    def connect(self) -> None:
        self.client.connect(self.config.host, self.config.port, self.config.keepalive_seconds)
        self.client.loop_start()
        LOGGER.info("Connected MQTT publisher to %s:%s", self.config.host, self.config.port)

    def publish_telemetry(self, payload: MonitoringPayload) -> None:
        topic = topic_for(TOPIC_TELEMETRY, self.device_id)
        body = json.dumps(payload.to_dict(), separators=(",", ":"))
        result = self.client.publish(topic, body, qos=self.config.qos)
        if result.rc != mqtt.MQTT_ERR_SUCCESS:
            LOGGER.warning("MQTT telemetry publish failed with code %s", result.rc)

    def publish_heartbeat(self) -> None:
        topic = topic_for(TOPIC_HEARTBEAT, self.device_id)
        body = json.dumps({"device_id": self.device_id, "timestamp": utc_now_iso()})
        self.client.publish(topic, body, qos=0)

    def stop(self) -> None:
        self.client.loop_stop()
        self.client.disconnect()
