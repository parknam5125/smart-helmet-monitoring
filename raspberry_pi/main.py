"""Raspberry Pi entry point for real-time helmet monitoring."""

from __future__ import annotations

import base64
import logging
import signal
import time

import cv2

from raspberry_pi.camera.video_capture import ThreadedVideoCapture
from raspberry_pi.networking.gstreamer_streamer import GStreamerStreamer
from raspberry_pi.networking.mjpeg_server import MjpegStreamServer, SharedFrameBuffer
from raspberry_pi.networking.mqtt_client import MQTTPublisher
from raspberry_pi.sensors.audio_sensor import NoiseMeter
from raspberry_pi.sensors.dht22_sensor import DHT22Sensor
from shared.config import load_settings
from shared.models import DetectionStatus, MonitoringPayload, SensorReading, utc_now_iso


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
LOGGER = logging.getLogger("raspberry_pi.main")


def encode_frame_jpeg(frame, quality: int = 80) -> str | None:
    ok, encoded = cv2.imencode(
        ".jpg",
        frame,
        [int(cv2.IMWRITE_JPEG_QUALITY), quality],
    )
    if not ok:
        return None
    return base64.b64encode(encoded).decode("ascii")


def main() -> None:
    settings = load_settings()
    stop_requested = False

    def handle_signal(signum: int, _frame: object) -> None:
        nonlocal stop_requested
        LOGGER.info("Received signal %s, stopping", signum)
        stop_requested = True

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    camera = ThreadedVideoCapture(
        settings.detector.camera_index,
        settings.detector.frame_width,
        settings.detector.frame_height,
    )
    dht22 = DHT22Sensor(settings.sensors.dht22_pin, settings.sensors.mock_sensors)
    noise_meter = NoiseMeter(
        settings.sensors.audio_sample_rate,
        settings.sensors.audio_window_seconds,
        settings.sensors.mock_sensors,
    )
    mqtt = MQTTPublisher(settings.mqtt, settings.device_id)

    frame_buffer = SharedFrameBuffer()
    mjpeg_server = (
        MjpegStreamServer(settings.stream.mjpeg_host, settings.stream.mjpeg_port, frame_buffer)
        if settings.stream.mjpeg_enabled
        else None
    )
    gst_streamer = (
        GStreamerStreamer(
            settings.stream.gstreamer_host,
            settings.stream.gstreamer_port,
            settings.detector.frame_width,
            settings.detector.frame_height,
            20,
            settings.stream.gstreamer_bitrate,
        )
        if settings.stream.gstreamer_enabled
        else None
    )

    try:
        camera.start()
        mqtt.connect()
        if mjpeg_server:
            mjpeg_server.start()
        if gst_streamer:
            gst_streamer.start()

        last_publish = 0.0
        publish_interval = 1.0 / settings.detector.publish_hz

        last_temperature = None
        last_noise = None

        LOGGER.info("Raspberry Pi camera/sensor publishing loop started")
        while not stop_requested:
            frame = camera.read()
            if frame is None:
                time.sleep(0.01)
                continue

            preview = frame.copy()
            overlay = f"T={last_temperature if last_temperature is not None else 'N/A'}C  N={last_noise if last_noise is not None else 'N/A'}dB  FPS={camera.fps:.1f}"
            cv2.putText(
                preview,
                overlay,
                (10, preview.shape[0] - 14),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                (255, 255, 255),
                2,
                cv2.LINE_AA,
            )

            frame_buffer.update(preview)
            if gst_streamer:
                gst_streamer.write(preview)

            now = time.monotonic()
            if now - last_publish >= publish_interval:
                last_temperature = dht22.read_temperature_c(
                    settings.sensors.temperature_interval_seconds
                )
                last_noise = noise_meter.read_db()
                frame_jpeg_b64 = encode_frame_jpeg(frame)
                if frame_jpeg_b64 is None:
                    LOGGER.warning("Skipping telemetry publish because JPEG encoding failed")
                    continue

                payload = MonitoringPayload(
                    device_id=settings.device_id,
                    timestamp=utc_now_iso(),
                    detection=DetectionStatus(),
                    sensor=SensorReading(
                        temperature_c=last_temperature,
                        noise_db=last_noise,
                    ),
                    metadata={
                        "camera_fps": round(camera.fps, 2),
                        "mjpeg_url": f"http://{settings.stream.mjpeg_host}:{settings.stream.mjpeg_port}/video"
                        if settings.stream.mjpeg_enabled
                        else None,
                        "gstreamer": {
                            "enabled": settings.stream.gstreamer_enabled,
                            "host": settings.stream.gstreamer_host,
                            "port": settings.stream.gstreamer_port,
                        },
                        "frame_mime_type": "image/jpeg",
                        "frame_jpeg_b64": frame_jpeg_b64,
                    },
                )
                mqtt.publish_telemetry(payload)
                mqtt.publish_heartbeat()
                last_publish = now

            if settings.detector.display_enabled:
                cv2.imshow("Safety Helmet Camera Publisher", preview)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break

    finally:
        LOGGER.info("Cleaning up Raspberry Pi components")
        dht22.close()
        mqtt.stop()
        if gst_streamer:
            gst_streamer.stop()
        if mjpeg_server:
            mjpeg_server.stop()
        camera.stop()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
