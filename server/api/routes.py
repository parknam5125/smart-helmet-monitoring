"""HTTP and WebSocket APIs used by the existing frontend."""

from __future__ import annotations

import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from server.database.db_manager import DatabaseManager
from server.networking.connection_manager import ConnectionManager


def create_router(db: DatabaseManager, manager: ConnectionManager) -> APIRouter:
    router = APIRouter()

    @router.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @router.get("/api/latest")
    async def latest(device_id: str | None = None) -> dict[str, object] | None:
        cached = await manager.latest(device_id)
        if cached:
            return cached if isinstance(cached, dict) else {"devices": cached}
        return db.latest(device_id)

    @router.get("/api/logs")
    async def logs(limit: int = 100, device_id: str | None = None) -> dict[str, object]:
        return {"items": db.list_logs(limit=limit, device_id=device_id)}

    @router.get("/api/risk/{device_id}")
    async def risk(device_id: str) -> dict[str, object] | None:
        cached = await manager.latest(device_id)
        if isinstance(cached, dict):
            return cached.get("assessment")
        row = db.latest(device_id)
        if not row:
            return None
        return json.loads(str(row["raw_assessment"]))

    @router.websocket("/ws/monitoring")
    async def websocket_endpoint(websocket: WebSocket) -> None:
        await manager.connect(websocket)
        try:
            while True:
                await websocket.receive_text()
        except WebSocketDisconnect:
            await manager.disconnect(websocket)

    return router
