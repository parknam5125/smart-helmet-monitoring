"""Run helmet detection on a video file and save an annotated demo output."""

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
LOGGER = logging.getLogger("raspberry_pi.demo_video")


def parse_args() -> argparse.Namespace:
    settings = load_settings()
    parser = argparse.ArgumentParser(
        description="Detect hardhat/no-hardhat classes from an mp4 file."
    )
    parser.add_argument(
        "--input",
        required=True,
        help="Input video path, for example C:\\path\\sample.mp4",
    )
    parser.add_argument(
        "--output",
        default="demo_outputs/sample_annotated.mp4",
        help="Annotated output video path.",
    )
    parser.add_argument(
        "--preview",
        default="demo_outputs/sample_preview.jpg",
        help="Annotated preview image path.",
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
        "--max-frames",
        type=int,
        default=0,
        help="Stop after this many frames. Use 0 to process the whole video.",
    )
    parser.add_argument(
        "--display",
        action="store_true",
        help="Open a live OpenCV preview window while processing.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_path = Path(args.input)
    output_path = Path(args.output)
    preview_path = Path(args.preview)

    if not input_path.exists():
        raise FileNotFoundError(f"Input video not found: {input_path}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    preview_path.parent.mkdir(parents=True, exist_ok=True)

    detector = YoloHelmetDetector(
        model_path=args.model,
        confidence_threshold=args.confidence,
        iou_threshold=args.iou,
        image_size=args.imgsz,
    )

    cap = cv2.VideoCapture(str(input_path))
    if not cap.isOpened():
        raise RuntimeError(f"Could not open video: {input_path}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 24.0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    writer = cv2.VideoWriter(
        str(output_path),
        cv2.VideoWriter_fourcc(*"mp4v"),
        fps,
        (width, height),
    )
    if not writer.isOpened():
        raise RuntimeError(f"Could not open output writer: {output_path}")

    LOGGER.info(
        "Processing %s: %sx%s, %.1f fps, %s frames",
        input_path,
        width,
        height,
        fps,
        total_frames,
    )

    frame_skip = max(1, args.frame_skip)
    processed = 0
    hardhat_frames = 0
    no_hardhat_frames = 0
    last_status = None
    start = time.monotonic()

    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break

            processed += 1
            if last_status is None or (processed - 1) % frame_skip == 0:
                last_status = detector.detect(frame)

            if last_status.helmet_count > 0:
                hardhat_frames += 1
            if last_status.no_helmet_count > 0:
                no_hardhat_frames += 1

            annotated = detector.draw(frame, last_status)
            cv2.putText(
                annotated,
                f"Frame {processed}/{total_frames or '?'}",
                (10, 88),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (255, 255, 255),
                2,
                cv2.LINE_AA,
            )
            writer.write(annotated)

            if processed == 1 or (
                last_status.no_helmet_count > 0 and not preview_path.exists()
            ):
                cv2.imwrite(str(preview_path), annotated)

            if args.display:
                cv2.imshow("Video Helmet Detection Demo", annotated)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break

            if args.max_frames > 0 and processed >= args.max_frames:
                break
    finally:
        cap.release()
        writer.release()
        cv2.destroyAllWindows()

    elapsed = max(0.001, time.monotonic() - start)
    LOGGER.info("Output video: %s", output_path)
    LOGGER.info("Preview image: %s", preview_path)
    LOGGER.info(
        "Processed %s frames in %.1fs (%.1f fps). Hardhat frames=%s, NO-Hardhat frames=%s",
        processed,
        elapsed,
        processed / elapsed,
        hardhat_frames,
        no_hardhat_frames,
    )


if __name__ == "__main__":
    main()
