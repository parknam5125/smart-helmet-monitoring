"""Show live YOLO helmet detection from a camera index or video file."""

from __future__ import annotations

import argparse
import logging
import time
from pathlib import Path

import cv2

from raspberry_pi.detection.yolo_detector import YoloHelmetDetector
from shared.config import load_settings


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
LOGGER = logging.getLogger("raspberry_pi.live_video_demo")


def parse_args() -> argparse.Namespace:
    settings = load_settings()
    parser = argparse.ArgumentParser(
        description="Open a live OpenCV window with helmet bounding boxes."
    )
    parser.add_argument(
        "--source",
        required=True,
        help="Camera index such as 0, or a video path such as sample.mp4.",
    )
    parser.add_argument(
        "--model",
        default=settings.detector.model_path,
        help="YOLOv8 model path.",
    )
    parser.add_argument(
        "--confidence",
        type=float,
        default=settings.detector.confidence_threshold,
        help="Detection confidence threshold.",
    )
    parser.add_argument(
        "--iou",
        type=float,
        default=settings.detector.iou_threshold,
        help="Detection IOU threshold.",
    )
    parser.add_argument(
        "--imgsz",
        type=int,
        default=settings.detector.image_size,
        help="YOLO inference image size.",
    )
    parser.add_argument(
        "--frame-skip",
        type=int,
        default=1,
        help="Run YOLO every N frames and reuse the previous result between detections.",
    )
    parser.add_argument(
        "--loop",
        action="store_true",
        help="Loop a video file when it reaches the end.",
    )
    parser.add_argument(
        "--realtime",
        action="store_true",
        help="Throttle video-file playback to the source FPS.",
    )
    return parser.parse_args()


def open_capture(source: str) -> cv2.VideoCapture:
    if source.isdigit():
        cap = cv2.VideoCapture(int(source))
    else:
        path = Path(source)
        if not path.exists():
            raise FileNotFoundError(f"Video source not found: {path}")
        cap = cv2.VideoCapture(str(path))

    if not cap.isOpened():
        raise RuntimeError(f"Could not open source: {source}")
    return cap


def main() -> None:
    args = parse_args()
    detector = YoloHelmetDetector(
        model_path=args.model,
        confidence_threshold=args.confidence,
        iou_threshold=args.iou,
        image_size=args.imgsz,
    )

    cap = open_capture(args.source)
    fps = cap.get(cv2.CAP_PROP_FPS) or 24.0
    frame_delay = 1.0 / fps if args.realtime and not args.source.isdigit() else 0.0
    frame_skip = max(1, args.frame_skip)
    frame_index = 0
    last_status = None
    last_tick = time.monotonic()
    measured_fps = 0.0
    fps_frames = 0
    fps_started = time.monotonic()

    LOGGER.info("Press q in the OpenCV window to quit.")

    try:
        while True:
            frame_started = time.monotonic()
            ok, frame = cap.read()
            if not ok:
                if args.loop and not args.source.isdigit():
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    frame_index = 0
                    last_status = None
                    continue
                break

            frame_index += 1
            if last_status is None or (frame_index - 1) % frame_skip == 0:
                last_status = detector.detect(frame)

            annotated = detector.draw(frame, last_status)
            fps_frames += 1
            elapsed = time.monotonic() - fps_started
            if elapsed >= 1.0:
                measured_fps = fps_frames / elapsed
                fps_frames = 0
                fps_started = time.monotonic()

            cv2.putText(
                annotated,
                f"Live demo | FPS {measured_fps:.1f} | q: quit",
                (10, annotated.shape[0] - 16),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.65,
                (255, 255, 255),
                2,
                cv2.LINE_AA,
            )

            cv2.imshow("Safety Helmet Live Detection", annotated)
            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                break

            if frame_delay > 0:
                spent = time.monotonic() - frame_started
                if spent < frame_delay:
                    time.sleep(frame_delay - spent)

            last_tick = frame_started
    finally:
        cap.release()
        cv2.destroyAllWindows()
        LOGGER.info("Live demo stopped")


if __name__ == "__main__":
    main()
