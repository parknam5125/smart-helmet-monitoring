"""YOLOv8 helmet/person/no-helmet detection and frame annotation."""

from __future__ import annotations

import logging
import os
from pathlib import Path

import cv2
import numpy as np

os.environ.setdefault("YOLO_CONFIG_DIR", str(Path.cwd() / ".ultralytics"))

from ultralytics import YOLO

from shared.models import DetectionBox, DetectionStatus


LOGGER = logging.getLogger(__name__)

PERSON_NAMES = {"person", "worker", "human"}
HELMET_NAMES = {"helmet", "hardhat", "hard_hat", "safety helmet", "safety_helmet"}
NO_HELMET_NAMES = {
    "no helmet",
    "no_helmet",
    "no-hardhat",
    "no_hardhat",
    "head",
    "no safety helmet",
}


class YoloHelmetDetector:
    def __init__(
        self,
        model_path: str,
        confidence_threshold: float,
        iou_threshold: float,
        image_size: int,
    ) -> None:
        if not Path(model_path).exists():
            raise FileNotFoundError(
                f"YOLO model not found at {model_path}. Set YOLO_MODEL_PATH to a trained helmet model."
            )
        self.model = YOLO(model_path)
        self.confidence_threshold = confidence_threshold
        self.iou_threshold = iou_threshold
        self.image_size = image_size
        LOGGER.info("Loaded YOLO model from %s", model_path)

    def detect(self, frame: np.ndarray) -> DetectionStatus:
        results = self.model.predict(
            frame,
            imgsz=self.image_size,
            conf=self.confidence_threshold,
            iou=self.iou_threshold,
            verbose=False,
        )
        boxes: list[DetectionBox] = []
        confidences: list[float] = []
        person_count = 0
        helmet_count = 0
        no_helmet_count = 0

        for result in results:
            names = result.names
            for raw_box in result.boxes:
                cls_id = int(raw_box.cls[0])
                conf = float(raw_box.conf[0])
                x1, y1, x2, y2 = [int(v) for v in raw_box.xyxy[0].tolist()]
                class_name = str(names.get(cls_id, cls_id)).strip()
                normalized = class_name.lower().replace("-", "_")

                if normalized in PERSON_NAMES:
                    person_count += 1
                elif normalized in HELMET_NAMES:
                    helmet_count += 1
                elif normalized in NO_HELMET_NAMES:
                    no_helmet_count += 1

                confidences.append(conf)
                boxes.append(
                    DetectionBox(
                        class_name=class_name,
                        confidence=conf,
                        x1=x1,
                        y1=y1,
                        x2=x2,
                        y2=y2,
                    )
                )

        helmet_detected = helmet_count > 0 and no_helmet_count == 0
        avg_conf = sum(confidences) / len(confidences) if confidences else 0.0
        return DetectionStatus(
            person_count=person_count,
            helmet_count=helmet_count,
            no_helmet_count=no_helmet_count,
            helmet_detected=helmet_detected,
            avg_confidence=avg_conf,
            boxes=boxes,
        )

    @staticmethod
    def draw(frame: np.ndarray, status: DetectionStatus) -> np.ndarray:
        annotated = frame.copy()
        for box in status.boxes:
            name = box.class_name.lower().replace("-", "_")
            if name in HELMET_NAMES:
                color = (40, 180, 40)
            elif name in NO_HELMET_NAMES:
                color = (30, 30, 230)
            else:
                color = (255, 180, 40)

            cv2.rectangle(annotated, (box.x1, box.y1), (box.x2, box.y2), color, 2)
            label = f"{box.class_name} {box.confidence:.2f}"
            label_size, baseline = cv2.getTextSize(
                label, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 2
            )
            top = max(box.y1, label_size[1] + 8)
            cv2.rectangle(
                annotated,
                (box.x1, top - label_size[1] - 8),
                (box.x1 + label_size[0] + 8, top + baseline - 3),
                color,
                -1,
            )
            cv2.putText(
                annotated,
                label,
                (box.x1 + 4, top - 5),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                (255, 255, 255),
                2,
                cv2.LINE_AA,
            )

        if status.no_helmet_count > 0:
            state_text = "NO HELMET"
            state_color = (30, 30, 230)
        elif status.helmet_detected:
            state_text = "HELMET OK"
            state_color = (40, 180, 40)
        else:
            state_text = "NO PERSON / UNKNOWN"
            state_color = (80, 140, 240)

        cv2.rectangle(annotated, (10, 10), (270, 58), state_color, -1)
        cv2.putText(
            annotated,
            state_text,
            (22, 43),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (255, 255, 255),
            2,
            cv2.LINE_AA,
        )
        return annotated

