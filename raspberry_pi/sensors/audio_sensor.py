"""Microphone noise level estimation."""

from __future__ import annotations

import logging
import math
import random

import numpy as np


LOGGER = logging.getLogger(__name__)


class NoiseMeter:
    def __init__(self, sample_rate: int, window_seconds: float, mock: bool = False) -> None:
        self.sample_rate = sample_rate
        self.window_seconds = window_seconds
        self.mock = mock
        self._sounddevice = None

        if self.mock:
            LOGGER.warning("Noise meter mock mode is enabled")
            return

        try:
            import sounddevice as sd

            self._sounddevice = sd
        except Exception as exc:  # pragma: no cover - host dependent
            LOGGER.warning("sounddevice unavailable: %s", exc)

    def read_db(self) -> float | None:
        if self.mock:
            return round(random.uniform(55.0, 105.0), 1)
        if self._sounddevice is None:
            return None

        frames = max(1, int(self.sample_rate * self.window_seconds))
        try:
            recording = self._sounddevice.rec(
                frames,
                samplerate=self.sample_rate,
                channels=1,
                dtype="float32",
                blocking=True,
            )
        except Exception as exc:  # pragma: no cover - host dependent
            LOGGER.warning("Microphone read failed: %s", exc)
            return None

        samples = np.asarray(recording, dtype=np.float32).reshape(-1)
        rms = float(np.sqrt(np.mean(np.square(samples)))) if samples.size else 0.0
        if rms <= 0.000001:
            return 0.0

        # Consumer microphones are not calibrated SPL meters. This maps digital RMS
        # to a stable demo dB scale; calibrate this offset for a real deployment.
        db = 20.0 * math.log10(rms) + 94.0
        return round(max(0.0, db), 1)
