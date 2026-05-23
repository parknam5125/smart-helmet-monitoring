"""Optional OpenCV-to-GStreamer RTP/H264 video sender."""

from __future__ import annotations

import logging

import cv2
import numpy as np


LOGGER = logging.getLogger(__name__)


class GStreamerStreamer:
    def __init__(
        self,
        host: str,
        port: int,
        width: int,
        height: int,
        fps: int,
        bitrate: int,
    ) -> None:
        self.host = host
        self.port = port
        self.width = width
        self.height = height
        self.fps = fps
        self.bitrate = bitrate
        self._writer: cv2.VideoWriter | None = None

    def start(self) -> None:
        pipeline = (
            "appsrc ! videoconvert ! video/x-raw,format=I420 ! "
            f"x264enc tune=zerolatency bitrate={self.bitrate} speed-preset=ultrafast ! "
            f"rtph264pay config-interval=1 pt=96 ! udpsink host={self.host} port={self.port}"
        )
        self._writer = cv2.VideoWriter(
            pipeline,
            cv2.CAP_GSTREAMER,
            0,
            float(self.fps),
            (self.width, self.height),
            True,
        )
        if not self._writer.isOpened():
            raise RuntimeError(
                "Failed to open GStreamer writer. Install GStreamer and OpenCV GStreamer support."
            )
        LOGGER.info("GStreamer RTP stream enabled to udp://%s:%s", self.host, self.port)

    def write(self, frame: np.ndarray) -> None:
        if self._writer is not None:
            self._writer.write(frame)

    def stop(self) -> None:
        if self._writer is not None:
            self._writer.release()
