"""WebSocket connection manager and latest-state cache."""

from __future__ import annotations

import asyncio
from typing import Any

from fastapi import WebSocket


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: set[WebSocket] = set()
        self._latest_by_device: dict[str, dict[str, Any]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._connections.add(websocket)
            latest = list(self._latest_by_device.values())
        for item in latest:
            await websocket.send_json(item)

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            self._connections.discard(websocket)

    async def publish(self, device_id: str, data: dict[str, Any]) -> None:
        async with self._lock:
            self._latest_by_device[device_id] = data
            connections = list(self._connections)

        failed: list[WebSocket] = []
        for websocket in connections:
            try:
                await websocket.send_json(data)
            except Exception:
                failed.append(websocket)

        if failed:
            async with self._lock:
                for websocket in failed:
                    self._connections.discard(websocket)

    async def latest(self, device_id: str | None = None) -> dict[str, Any] | list[dict[str, Any]] | None:
        async with self._lock:
            if device_id:
                return self._latest_by_device.get(device_id)
            return list(self._latest_by_device.values())
