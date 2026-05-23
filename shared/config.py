"""Environment-driven configuration shared by Pi and server apps."""

from __future__ import annotations

import os
from dataclasses import dataclass


def _get_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y", "on"}


def _get_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    return int(raw)


def _get_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    return float(raw)


@dataclass(frozen=True, slots=True)
class MQTTConfig:
    host: str = "localhost"
    port: int = 1883
    username: str | None = None
    password: str | None = None
    keepalive_seconds: int = 30
    qos: int = 1


@dataclass(frozen=True, slots=True)
class DetectorConfig:
    model_path: str = "models/helmet_yolov8s_hardhat.pt"
    camera_index: int = 0
    frame_width: int = 640
    frame_height: int = 480
    confidence_threshold: float = 0.45
    iou_threshold: float = 0.45
    image_size: int = 416
    frame_skip: int = 1
    display_enabled: bool = True
    publish_hz: float = 2.0


@dataclass(frozen=True, slots=True)
class SensorConfig:
    dht22_pin: str = "D4"
    temperature_interval_seconds: float = 2.0
    audio_sample_rate: int = 16000
    audio_window_seconds: float = 0.25
    mock_sensors: bool = False


@dataclass(frozen=True, slots=True)
class StreamConfig:
    mjpeg_enabled: bool = True
    mjpeg_host: str = "0.0.0.0"
    mjpeg_port: int = 8090
    gstreamer_enabled: bool = False
    gstreamer_host: str = "127.0.0.1"
    gstreamer_port: int = 5000
    gstreamer_bitrate: int = 900


@dataclass(frozen=True, slots=True)
class RiskConfig:
    case_library_path: str = "server/cbr/case_library.json"
    warning_threshold: float = 35.0
    danger_threshold: float = 70.0
    high_temperature_c: float = 32.0
    critical_temperature_c: float = 38.0
    loud_noise_db: float = 85.0
    critical_noise_db: float = 100.0
    unsafe_duration_warning_seconds: float = 5.0
    unsafe_duration_danger_seconds: float = 15.0
    repeat_window_seconds: float = 120.0


@dataclass(frozen=True, slots=True)
class ServerConfig:
    host: str = "0.0.0.0"
    port: int = 8000
    database_path: str = "server/database/safety_monitor.db"
    api_cors_origins: tuple[str, ...] = ("*",)


@dataclass(frozen=True, slots=True)
class Settings:
    device_id: str
    mqtt: MQTTConfig
    detector: DetectorConfig
    sensors: SensorConfig
    stream: StreamConfig
    risk: RiskConfig
    server: ServerConfig


def load_settings() -> Settings:
    username = os.getenv("MQTT_USERNAME") or None
    password = os.getenv("MQTT_PASSWORD") or None
    origins = tuple(
        item.strip()
        for item in os.getenv("API_CORS_ORIGINS", "*").split(",")
        if item.strip()
    )

    return Settings(
        device_id=os.getenv("DEVICE_ID", "helmet-pi-01"),
        mqtt=MQTTConfig(
            host=os.getenv("MQTT_HOST", "localhost"),
            port=_get_int("MQTT_PORT", 1883),
            username=username,
            password=password,
            keepalive_seconds=_get_int("MQTT_KEEPALIVE_SECONDS", 30),
            qos=_get_int("MQTT_QOS", 1),
        ),
        detector=DetectorConfig(
            model_path=os.getenv(
                "YOLO_MODEL_PATH",
                "models/helmet_yolov8s_hardhat.pt",
            ),
            camera_index=_get_int("CAMERA_INDEX", 0),
            frame_width=_get_int("FRAME_WIDTH", 640),
            frame_height=_get_int("FRAME_HEIGHT", 480),
            confidence_threshold=_get_float("YOLO_CONFIDENCE", 0.45),
            iou_threshold=_get_float("YOLO_IOU", 0.45),
            image_size=_get_int("YOLO_IMAGE_SIZE", 416),
            frame_skip=max(1, _get_int("FRAME_SKIP", 1)),
            display_enabled=_get_bool("DISPLAY_ENABLED", True),
            publish_hz=max(0.2, _get_float("PUBLISH_HZ", 2.0)),
        ),
        sensors=SensorConfig(
            dht22_pin=os.getenv("DHT22_PIN", "D4"),
            temperature_interval_seconds=max(
                1.0, _get_float("TEMPERATURE_INTERVAL_SECONDS", 2.0)
            ),
            audio_sample_rate=_get_int("AUDIO_SAMPLE_RATE", 16000),
            audio_window_seconds=max(0.1, _get_float("AUDIO_WINDOW_SECONDS", 0.25)),
            mock_sensors=_get_bool("MOCK_SENSORS", False),
        ),
        stream=StreamConfig(
            mjpeg_enabled=_get_bool("MJPEG_ENABLED", True),
            mjpeg_host=os.getenv("MJPEG_HOST", "0.0.0.0"),
            mjpeg_port=_get_int("MJPEG_PORT", 8090),
            gstreamer_enabled=_get_bool("GSTREAMER_ENABLED", False),
            gstreamer_host=os.getenv("GSTREAMER_HOST", "127.0.0.1"),
            gstreamer_port=_get_int("GSTREAMER_PORT", 5000),
            gstreamer_bitrate=_get_int("GSTREAMER_BITRATE", 900),
        ),
        risk=RiskConfig(
            case_library_path=os.getenv(
                "CASE_LIBRARY_PATH",
                "server/cbr/case_library.json",
            ),
            warning_threshold=_get_float("RISK_WARNING_THRESHOLD", 35.0),
            danger_threshold=_get_float("RISK_DANGER_THRESHOLD", 70.0),
            high_temperature_c=_get_float("HIGH_TEMPERATURE_C", 32.0),
            critical_temperature_c=_get_float("CRITICAL_TEMPERATURE_C", 38.0),
            loud_noise_db=_get_float("LOUD_NOISE_DB", 85.0),
            critical_noise_db=_get_float("CRITICAL_NOISE_DB", 100.0),
            unsafe_duration_warning_seconds=_get_float(
                "UNSAFE_DURATION_WARNING_SECONDS", 5.0
            ),
            unsafe_duration_danger_seconds=_get_float(
                "UNSAFE_DURATION_DANGER_SECONDS", 15.0
            ),
            repeat_window_seconds=_get_float("REPEAT_WINDOW_SECONDS", 120.0),
        ),
        server=ServerConfig(
            host=os.getenv("SERVER_HOST", "0.0.0.0"),
            port=_get_int("SERVER_PORT", 8000),
            database_path=os.getenv(
                "DATABASE_PATH", "server/database/safety_monitor.db"
            ),
            api_cors_origins=origins or ("*",),
        ),
    )
