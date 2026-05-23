"""Threaded OpenCV camera capture for low-latency latest-frame reads."""

from __future__ import annotations

import logging
import threading
import time
from typing import Optional

import cv2
import numpy as np


LOGGER = logging.getLogger(__name__)


class ThreadedVideoCapture:
    def __init__(self, camera_index: int, width: int, height: int) -> None:
        self.camera_index = camera_index
        self.width = width
        self.height = height
        self._capture: Optional[cv2.VideoCapture] = None
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._latest_frame: Optional[np.ndarray] = None
        self._running = threading.Event()
        self._fps = 0.0

    @property
    def fps(self) -> float:
        return self._fps

    def start(self) -> None:
        if self._running.is_set():
            return
        self._capture = cv2.VideoCapture(self.camera_index)
        self._capture.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self._capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        if not self._capture.isOpened():
            raise RuntimeError(f"Cannot open camera index {self.camera_index}")
        self._running.set()
        self._thread = threading.Thread(target=self._reader, name="camera-reader", daemon=True)
        self._thread.start()
        LOGGER.info("Camera started on index %s", self.camera_index)

    def _reader(self) -> None:
        frames = 0
        started = time.monotonic()
        assert self._capture is not None
        while self._running.is_set():
            ok, frame = self._capture.read()
            if not ok:
                LOGGER.warning("Camera frame read failed")
                time.sleep(0.05)
                continue
            with self._lock:
                self._latest_frame = frame
            frames += 1
            elapsed = time.monotonic() - started
            if elapsed >= 1.0:
                self._fps = frames / elapsed
                frames = 0
                started = time.monotonic()

    def read(self) -> Optional[np.ndarray]:
        with self._lock:
            if self._latest_frame is None:
                return None
            return self._latest_frame.copy()

    def stop(self) -> None:
        self._running.clear()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        if self._capture:
            self._capture.release()
        LOGGER.info("Camera stopped")
