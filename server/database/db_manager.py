"""SQLite database initialization and query helpers."""

from __future__ import annotations

import json
import sqlite3
import threading
from pathlib import Path
from typing import Any

from shared.models import MonitoringPayload, RiskAssessment


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS monitoring_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id TEXT NOT NULL,
    payload_timestamp TEXT NOT NULL,
    assessment_timestamp TEXT NOT NULL,
    temperature_c REAL,
    noise_db REAL,
    person_count INTEGER NOT NULL,
    helmet_count INTEGER NOT NULL,
    no_helmet_count INTEGER NOT NULL,
    helmet_detected INTEGER NOT NULL,
    risk_level TEXT NOT NULL,
    risk_score REAL NOT NULL,
    matched_case_id TEXT,
    similarity REAL NOT NULL,
    event_summary TEXT NOT NULL,
    raw_payload TEXT NOT NULL,
    raw_assessment TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_monitoring_device_time
ON monitoring_logs(device_id, payload_timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_monitoring_risk
ON monitoring_logs(risk_level, payload_timestamp DESC);
"""


class DatabaseManager:
    def __init__(self, database_path: str) -> None:
        self.database_path = database_path
        Path(database_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(database_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.Lock()

    def initialize(self) -> None:
        with self._lock:
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.executescript(SCHEMA_SQL)
            self._conn.commit()

    def insert_monitoring_result(
        self,
        payload: MonitoringPayload,
        assessment: RiskAssessment,
    ) -> int:
        with self._lock:
            cursor = self._conn.execute(
                """
                INSERT INTO monitoring_logs (
                    device_id, payload_timestamp, assessment_timestamp,
                    temperature_c, noise_db, person_count, helmet_count,
                    no_helmet_count, helmet_detected, risk_level, risk_score,
                    matched_case_id, similarity, event_summary,
                    raw_payload, raw_assessment
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payload.device_id,
                    payload.timestamp,
                    assessment.timestamp,
                    payload.sensor.temperature_c,
                    payload.sensor.noise_db,
                    payload.detection.person_count,
                    payload.detection.helmet_count,
                    payload.detection.no_helmet_count,
                    int(payload.detection.helmet_detected),
                    assessment.risk_level.value,
                    assessment.risk_score,
                    assessment.matched_case_id,
                    assessment.similarity,
                    assessment.event_summary,
                    json.dumps(payload.to_dict(), ensure_ascii=False),
                    json.dumps(assessment.to_dict(), ensure_ascii=False),
                ),
            )
            self._conn.commit()
            return int(cursor.lastrowid)

    def latest(self, device_id: str | None = None) -> dict[str, Any] | None:
        query = "SELECT * FROM monitoring_logs"
        params: tuple[Any, ...] = ()
        if device_id:
            query += " WHERE device_id = ?"
            params = (device_id,)
        query += " ORDER BY id DESC LIMIT 1"
        with self._lock:
            row = self._conn.execute(query, params).fetchone()
        return dict(row) if row else None

    def list_logs(self, limit: int = 100, device_id: str | None = None) -> list[dict[str, Any]]:
        limit = max(1, min(limit, 1000))
        query = "SELECT * FROM monitoring_logs"
        params: list[Any] = []
        if device_id:
            query += " WHERE device_id = ?"
            params.append(device_id)
        query += " ORDER BY id DESC LIMIT ?"
        params.append(limit)
        with self._lock:
            rows = self._conn.execute(query, tuple(params)).fetchall()
        return [dict(row) for row in rows]

    def close(self) -> None:
        with self._lock:
            self._conn.close()
