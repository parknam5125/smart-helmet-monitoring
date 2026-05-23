"""DHT22 temperature reader with explicit mock mode for non-Pi demos."""

from __future__ import annotations

import logging
import random
import time
from typing import Any


LOGGER = logging.getLogger(__name__)


class DHT22Sensor:
    def __init__(self, pin_name: str, mock: bool = False) -> None:
        self.pin_name = pin_name
        self.mock = mock
        self._device: Any | None = None
        self._last_value: float | None = None
        self._last_read = 0.0

        if self.mock:
            LOGGER.warning("DHT22 mock mode is enabled")
            return

        try:
            import adafruit_dht
            import board

            pin = getattr(board, pin_name)
            self._device = adafruit_dht.DHT22(pin)
            LOGGER.info("DHT22 initialized on board.%s", pin_name)
        except Exception as exc:  # pragma: no cover - hardware dependent
            LOGGER.warning("DHT22 unavailable: %s", exc)
            self._device = None

    def read_temperature_c(self, min_interval_seconds: float) -> float | None:
        now = time.monotonic()
        if self._last_value is not None and now - self._last_read < min_interval_seconds:
            return self._last_value

        if self.mock:
            self._last_value = round(random.uniform(24.0, 37.5), 1)
            self._last_read = now
            return self._last_value

        if self._device is None:
            return None

        try:
            value = self._device.temperature
            if value is not None:
                self._last_value = float(value)
                self._last_read = now
            return self._last_value
        except RuntimeError as exc:  # DHT sensors often need retry.
            LOGGER.debug("DHT22 transient read failure: %s", exc)
            return self._last_value

    def close(self) -> None:
        if self._device is not None:
            try:
                self._device.exit()
            except Exception:
                LOGGER.debug("DHT22 cleanup failed", exc_info=True)
