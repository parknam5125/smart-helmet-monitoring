"""Server entry point for MQTT ingestion, server-side YOLO, CBR, SQLite, and FastAPI."""

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
from shared.detection.yolo_detector import YoloHelmetDetector


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
    detector = YoloHelmetDetector(
        settings.detector.model_path,
        settings.detector.confidence_threshold,
        settings.detector.iou_threshold,
        settings.detector.image_size,
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        loop = asyncio.get_running_loop()
        subscriber = MQTTSubscriber(settings, db, cbr, manager, detector, loop)
        app.state.mqtt_subscriber = subscriber
        subscriber.start()
        LOGGER.info("Backend server is ready")
        try:
            yield
        finally:
            subscriber.stop()
            db.close()
            LOGGER.info("Backend server stopped")

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
    print("Starting safety helmet backend server")
    print(f"API URL: http://localhost:{settings.server.port}")
    print("Press Ctrl+C to stop.")
    uvicorn.run(
        app,
        host=settings.server.host,
        port=settings.server.port,
        reload=False,
        log_level="warning",
        access_log=False,
    )
