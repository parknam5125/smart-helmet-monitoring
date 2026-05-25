"""Compatibility import for the shared YOLO detector."""

from shared.detection.yolo_detector import (
    HELMET_NAMES,
    NO_HELMET_NAMES,
    PERSON_NAMES,
    YoloHelmetDetector,
)

__all__ = [
    "HELMET_NAMES",
    "NO_HELMET_NAMES",
    "PERSON_NAMES",
    "YoloHelmetDetector",
]
