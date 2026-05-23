"""Server entry point for MQTT ingestion, CBR, SQLite, and FastAPI."""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from server.api.routes import create_router
from server.cbr.case_library import load_cases_from_json
from server.cbr.cbr_engine import CBREngine
from server.database.db_manager import DatabaseManager
from server.networking.connection_manager import ConnectionManager
from server.networking.mqtt_subscriber import MQTTSubscriber
from shared.config import load_settings


logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
)
LOGGER = logging.getLogger("server.main")


def create_app() -> FastAPI:
    settings = load_settings()
    db = DatabaseManager(settings.server.database_path)
    db.initialize()
    manager = ConnectionManager()
    cbr = CBREngine(
        settings.risk,
        cases=load_cases_from_json(settings.risk.case_library_path),
    )
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        loop = asyncio.get_running_loop()
        subscriber = MQTTSubscriber(settings, db, cbr, manager, loop)
        app.state.mqtt_subscriber = subscriber
        subscriber.start()
        LOGGER.info("백엔드 서버 준비 완료")
        try:
            yield
        finally:
            subscriber.stop()
            db.close()
            LOGGER.info("백엔드 서버가 종료되었습니다")

    app = FastAPI(
        title="Safety Helmet Monitoring API",
        version="1.0.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.server.api_cors_origins),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(create_router(db, manager))

    return app


app = create_app()


if __name__ == "__main__":
    settings = load_settings()
    print("스마트 안전모 백엔드 서버를 시작합니다.")
    print(f"API 주소: http://localhost:{settings.server.port}")
    print("종료하려면 Ctrl+C를 누르세요.")
    uvicorn.run(
        app,
        host=settings.server.host,
        port=settings.server.port,
        reload=False,
        log_level="warning",
        access_log=False,
    )
