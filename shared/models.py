"""Typed payloads passed between the Raspberry Pi and server."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class RiskLevel(str, Enum):
    SAFE = "SAFE"
    WARNING = "WARNING"
    DANGER = "DANGER"


@dataclass(slots=True)
class DetectionBox:
    class_name: str
    confidence: float
    x1: int
    y1: int
    x2: int
    y2: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class DetectionStatus:
    person_count: int = 0
    helmet_count: int = 0
    no_helmet_count: int = 0
    helmet_detected: bool = False
    avg_confidence: float = 0.0
    boxes: list[DetectionBox] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["boxes"] = [box.to_dict() for box in self.boxes]
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "DetectionStatus":
        if not data:
            return cls()
        boxes = [
            DetectionBox(**box)
            for box in data.get("boxes", [])
            if isinstance(box, dict)
        ]
        return cls(
            person_count=int(data.get("person_count", 0)),
            helmet_count=int(data.get("helmet_count", 0)),
            no_helmet_count=int(data.get("no_helmet_count", 0)),
            helmet_detected=bool(data.get("helmet_detected", False)),
            avg_confidence=float(data.get("avg_confidence", 0.0)),
            boxes=boxes,
        )


@dataclass(slots=True)
class SensorReading:
    temperature_c: float | None = None
    noise_db: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "SensorReading":
        if not data:
            return cls()
        temperature = data.get("temperature_c")
        noise = data.get("noise_db")
        return cls(
            temperature_c=float(temperature) if temperature is not None else None,
            noise_db=float(noise) if noise is not None else None,
        )


@dataclass(slots=True)
class MonitoringPayload:
    device_id: str
    timestamp: str
    detection: DetectionStatus
    sensor: SensorReading
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "device_id": self.device_id,
            "timestamp": self.timestamp,
            "detection": self.detection.to_dict(),
            "sensor": self.sensor.to_dict(),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MonitoringPayload":
        return cls(
            device_id=str(data["device_id"]),
            timestamp=str(data.get("timestamp") or utc_now_iso()),
            detection=DetectionStatus.from_dict(data.get("detection")),
            sensor=SensorReading.from_dict(data.get("sensor")),
            metadata=dict(data.get("metadata") or {}),
        )


@dataclass(slots=True)
class RiskAssessment:
    device_id: str
    timestamp: str
    risk_level: RiskLevel
    risk_score: float
    matched_case_id: str | None
    similarity: float
    event_summary: str
    factors: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "device_id": self.device_id,
            "timestamp": self.timestamp,
            "risk_level": self.risk_level.value,
            "risk_score": round(self.risk_score, 2),
            "matched_case_id": self.matched_case_id,
            "similarity": round(self.similarity, 3),
            "event_summary": self.event_summary,
            "factors": self.factors,
        }
