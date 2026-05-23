"""Project-wide constants and MQTT topic helpers."""

from __future__ import annotations


PROJECT_NAME = "AI-based Smart Safety Helmet Monitoring System"

RISK_SAFE = "SAFE"
RISK_WARNING = "WARNING"
RISK_DANGER = "DANGER"

TOPIC_TELEMETRY = "safety/{device_id}/telemetry"
TOPIC_RISK = "safety/{device_id}/risk"
TOPIC_HEARTBEAT = "safety/{device_id}/heartbeat"
TOPIC_COMMAND = "safety/{device_id}/command"
TOPIC_ALL_TELEMETRY = "safety/+/telemetry"


def topic_for(template: str, device_id: str) -> str:
    return template.format(device_id=device_id)
