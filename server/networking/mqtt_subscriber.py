"""MQTT ingestion that runs server-side YOLO, CBR, persistence, and WebSockets."""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import queue
import threading
import time
from collections import deque

import cv2
import numpy as np
import paho.mqtt.client as mqtt

from server.cbr.cbr_engine import CBREngine
from server.database.db_manager import DatabaseManager
from server.networking.connection_manager import ConnectionManager
from shared.config import Settings
from shared.constants import TOPIC_ALL_HEARTBEAT, TOPIC_ALL_TELEMETRY, TOPIC_RISK, topic_for
from shared.detection.yolo_detector import YoloHelmetDetector
from shared.models import MonitoringPayload, RiskAssessment, SensorReading


LOGGER = logging.getLogger(__name__)
DETECTION_WINDOW = "Server YOLO Helmet Detection"
SENSOR_PUBLISH_INTERVAL = 10.0  # seconds between sensor broadcasts
_YOLO_QUEUE_SIZE = 4            # drop oldest frames if worker falls behind


class MQTTSubscriber:
    def __init__(
        self,
        settings: Settings,
        db: DatabaseManager,
        cbr: CBREngine,
        connection_manager: ConnectionManager,
        detector: YoloHelmetDetector,
        loop: asyncio.AbstractEventLoop,
    ) -> None:
        self.settings = settings
        self.db = db
        self.cbr = cbr
        self.connection_manager = connection_manager
        self.detector = detector
        self.loop = loop
        self._assessment_cache: dict[str, tuple[float, RiskAssessment]] = {}
        self._sensor_buffer: dict[str, deque[tuple[float, SensorReading]]] = {}
        self._last_sensor_publish: dict[str, float] = {}
        self._frame_queue: queue.Queue[MonitoringPayload | None] = queue.Queue(
            maxsize=_YOLO_QUEUE_SIZE
        )
        self._worker_thread: threading.Thread | None = None
        self.client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2,
            client_id="safety-server-subscriber",
        )
        if settings.mqtt.username:
            self.client.username_pw_set(settings.mqtt.username, settings.mqtt.password)
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message

    def start(self) -> None:
        self._worker_thread = threading.Thread(
            target=self._yolo_worker,
            name="yolo-worker",
            daemon=True,
        )
        self._worker_thread.start()
        self.client.reconnect_delay_set(min_delay=1, max_delay=30)
        self.client.connect_async(
            self.settings.mqtt.host,
            self.settings.mqtt.port,
            self.settings.mqtt.keepalive_seconds,
        )
        self.client.loop_start()
        LOGGER.info(
            "MQTT subscriber connecting to %s:%s",
            self.settings.mqtt.host,
            self.settings.mqtt.port,
        )

    def stop(self) -> None:
        self.client.loop_stop()
        self.client.disconnect()
        self._frame_queue.put(None)  # sentinel: worker 종료 신호
        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=5.0)
        if self.settings.server.display_enabled:
            try:
                cv2.destroyWindow(DETECTION_WINDOW)
            except cv2.error:
                LOGGER.debug("Detection preview window was not open")

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
            client.subscribe(TOPIC_ALL_HEARTBEAT, qos=0)
            LOGGER.info("Waiting for Raspberry Pi telemetry on %s", TOPIC_ALL_TELEMETRY)
        else:
            LOGGER.error("MQTT connection failed: %s", reason_code)

    def _on_message(
        self,
        client: mqtt.Client,
        _userdata: object,
        message: mqtt.MQTTMessage,
    ) -> None:
        try:
            topic = str(message.topic)
            if topic.endswith("/heartbeat"):
                self._on_heartbeat(message)
                return

            raw = message.payload.decode("utf-8")
            payload = MonitoringPayload.from_dict(json.loads(raw))
            try:
                self._frame_queue.put_nowait(payload)
            except queue.Full:
                # 큐가 꽉 찼으면 가장 오래된 프레임을 버리고 최신 프레임 삽입
                try:
                    self._frame_queue.get_nowait()
                except queue.Empty:
                    pass
                try:
                    self._frame_queue.put_nowait(payload)
                except queue.Full:
                    LOGGER.debug("YOLO queue full, dropping frame from %s", payload.device_id)
        except Exception:
            LOGGER.exception("Error while processing MQTT message from %s", message.topic)

    def _yolo_worker(self) -> None:
        """별도 스레드에서 YOLO 추론, CBR, DB, WebSocket 처리."""
        while True:
            payload = self._frame_queue.get()
            if payload is None:  # sentinel 수신 → 종료
                break
            try:
                self._process_payload(payload)
            except Exception:
                LOGGER.exception("Error in YOLO worker for %s", payload.device_id)
            finally:
                self._frame_queue.task_done()

    def _process_payload(self, payload: MonitoringPayload) -> None:
        self._detect_payload_frame(payload)
        assessment = self._assess_payload(payload)
        row_id = self.db.insert_monitoring_result(payload, assessment)
        smoothed = self._accumulate_sensor(payload.device_id, payload.sensor)
        payload_dict = payload.to_dict()
        payload_dict["sensor"] = (
            smoothed.to_dict()
            if smoothed is not None
            else {"temperature_c": None, "noise_db": None}
        )
        event = {
            "type": "monitoring_update",
            "log_id": row_id,
            "payload": payload_dict,
            "assessment": assessment.to_dict(),
        }
        self.client.publish(
            topic_for(TOPIC_RISK, payload.device_id),
            json.dumps(assessment.to_dict(), separators=(",", ":")),
            qos=self.settings.mqtt.qos,
        )
        asyncio.run_coroutine_threadsafe(
            self.connection_manager.publish(payload.device_id, event),
            self.loop,
        )

    def _accumulate_sensor(
        self, device_id: str, reading: SensorReading
    ) -> SensorReading | None:
        now = time.monotonic()
        buf = self._sensor_buffer.setdefault(device_id, deque())
        buf.append((now, reading))
        while buf and now - buf[0][0] > SENSOR_PUBLISH_INTERVAL:
            buf.popleft()

        last_pub = self._last_sensor_publish.get(device_id, 0.0)
        if now - last_pub < SENSOR_PUBLISH_INTERVAL:
            return None

        temps = [r.temperature_c for _, r in buf if r.temperature_c is not None]
        noises = [r.noise_db for _, r in buf if r.noise_db is not None]
        self._last_sensor_publish[device_id] = now
        return SensorReading(
            temperature_c=sum(temps) / len(temps) if temps else None,
            noise_db=sum(noises) / len(noises) if noises else None,
        )

    def _assess_payload(self, payload: MonitoringPayload) -> RiskAssessment:
        now = time.monotonic()
        cached = self._assessment_cache.get(payload.device_id)
        interval = self.settings.risk.assessment_interval_seconds
        if cached is not None:
            assessed_at, assessment = cached
            if now - assessed_at < interval:
                return assessment

        assessment = self.cbr.assess(payload)
        self._assessment_cache[payload.device_id] = (now, assessment)
        return assessment

    def _on_heartbeat(self, message: mqtt.MQTTMessage) -> None:
        raw = message.payload.decode("utf-8")
        data = json.loads(raw)
        device_id = str(data.get("device_id") or message.topic.split("/")[1])
        timestamp = str(data.get("timestamp") or "")
        event = {
            "type": "device_status",
            "device_id": device_id,
            "connected": True,
            "timestamp": timestamp,
        }
        asyncio.run_coroutine_threadsafe(
            self.connection_manager.publish(device_id, event),
            self.loop,
        )

    def _detect_payload_frame(self, payload: MonitoringPayload) -> None:
        frame_b64 = payload.metadata.pop("frame_jpeg_b64", None)
        payload.metadata.pop("frame_mime_type", None)
        if not isinstance(frame_b64, str) or not frame_b64:
            return

        try:
            frame_bytes = base64.b64decode(frame_b64, validate=True)
            buffer = np.frombuffer(frame_bytes, dtype=np.uint8)
            frame = cv2.imdecode(buffer, cv2.IMREAD_COLOR)
            if frame is None:
                LOGGER.warning("Could not decode JPEG frame from %s", payload.device_id)
                return
            payload.detection = self.detector.detect(frame)
            self._show_detection_frame(frame, payload)
        except Exception:
            LOGGER.exception("Server-side YOLO detection failed for %s", payload.device_id)

    def _show_detection_frame(
        self,
        frame: np.ndarray,
        payload: MonitoringPayload,
    ) -> None:
        if not self.settings.server.display_enabled:
            return

        annotated = self.detector.draw(frame, payload.detection)
        overlay = f"{payload.device_id} | {payload.timestamp}"
        cv2.putText(
            annotated,
            overlay,
            (10, annotated.shape[0] - 14),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (255, 255, 255),
            2,
            cv2.LINE_AA,
        )
        try:
            cv2.imshow(DETECTION_WINDOW, annotated)
            cv2.waitKey(1)
        except cv2.error:
            LOGGER.exception("Could not render server detection preview window")
