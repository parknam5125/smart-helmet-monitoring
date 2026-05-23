"""Safety case library used by the CBR engine."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from shared.models import RiskLevel

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class SafetyCase:
    case_id: str
    description: str
    expected_risk: RiskLevel
    temperature_c: float
    noise_db: float
    no_helmet_count: int
    unsafe_duration_seconds: float
    repeat_count: int
    weights: dict[str, float]


DEFAULT_CASES: tuple[SafetyCase, ...] = (
    SafetyCase(
        case_id="SAFE_NORMAL_WORK",
        description="Normal temperature and noise with helmet detected",
        expected_risk=RiskLevel.SAFE,
        temperature_c=26.0,
        noise_db=65.0,
        no_helmet_count=0,
        unsafe_duration_seconds=0.0,
        repeat_count=0,
        weights={"temperature": 0.2, "noise": 0.2, "helmet": 0.35, "duration": 0.15, "repeat": 0.1},
    ),
    SafetyCase(
        case_id="WARNING_NO_HELMET_SHORT",
        description="Worker without helmet for a short duration",
        expected_risk=RiskLevel.WARNING,
        temperature_c=28.0,
        noise_db=70.0,
        no_helmet_count=1,
        unsafe_duration_seconds=6.0,
        repeat_count=1,
        weights={"temperature": 0.1, "noise": 0.1, "helmet": 0.45, "duration": 0.25, "repeat": 0.1},
    ),
    SafetyCase(
        case_id="DANGER_NO_HELMET_PERSISTENT",
        description="No helmet persists beyond the allowed unsafe duration",
        expected_risk=RiskLevel.DANGER,
        temperature_c=30.0,
        noise_db=78.0,
        no_helmet_count=1,
        unsafe_duration_seconds=20.0,
        repeat_count=3,
        weights={"temperature": 0.08, "noise": 0.07, "helmet": 0.4, "duration": 0.35, "repeat": 0.1},
    ),
    SafetyCase(
        case_id="WARNING_HOT_LOUD",
        description="Helmet present but environment is hot and loud",
        expected_risk=RiskLevel.WARNING,
        temperature_c=34.0,
        noise_db=90.0,
        no_helmet_count=0,
        unsafe_duration_seconds=0.0,
        repeat_count=1,
        weights={"temperature": 0.35, "noise": 0.35, "helmet": 0.15, "duration": 0.05, "repeat": 0.1},
    ),
    SafetyCase(
        case_id="DANGER_COMBINED_HAZARDS",
        description="No helmet combined with high temperature and critical noise",
        expected_risk=RiskLevel.DANGER,
        temperature_c=39.0,
        noise_db=103.0,
        no_helmet_count=1,
        unsafe_duration_seconds=12.0,
        repeat_count=4,
        weights={"temperature": 0.25, "noise": 0.25, "helmet": 0.25, "duration": 0.15, "repeat": 0.1},
    ),
)


def load_default_cases() -> tuple[SafetyCase, ...]:
    return DEFAULT_CASES


def _label_to_risk(label: str) -> RiskLevel:
    normalized = label.strip().upper()
    if normalized in {"HIGH", "DANGER"}:
        return RiskLevel.DANGER
    if normalized in {"MID", "MEDIUM", "WARNING"}:
        return RiskLevel.WARNING
    return RiskLevel.SAFE


def _case_weights(label: str) -> dict[str, float]:
    normalized = label.strip().upper()
    if normalized in {"HIGH", "DANGER"}:
        return {
            "temperature": 0.22,
            "noise": 0.34,
            "helmet": 0.28,
            "duration": 0.08,
            "repeat": 0.08,
        }
    if normalized in {"MID", "MEDIUM", "WARNING"}:
        return {
            "temperature": 0.24,
            "noise": 0.32,
            "helmet": 0.26,
            "duration": 0.1,
            "repeat": 0.08,
        }
    return {
        "temperature": 0.3,
        "noise": 0.3,
        "helmet": 0.25,
        "duration": 0.08,
        "repeat": 0.07,
    }


def _json_item_to_case(index: int, item: dict[str, Any]) -> SafetyCase:
    helmet_value = int(item.get("helmet", 0))
    label = str(item.get("label", "LOW"))
    return SafetyCase(
        case_id=f"JSON_{index:05d}_{label.upper()}",
        description=(
            f"Imported case: helmet={helmet_value}, "
            f"temp={float(item.get('temp', 0.0)):.1f}C, "
            f"noise={float(item.get('noise', 0.0)):.1f}dB, label={label}"
        ),
        expected_risk=_label_to_risk(label),
        temperature_c=float(item.get("temp", 0.0)),
        noise_db=float(item.get("noise", 0.0)),
        no_helmet_count=1 if helmet_value <= 0 else 0,
        unsafe_duration_seconds=0.0,
        repeat_count=0,
        weights=_case_weights(label),
    )


def load_cases_from_json(path: str) -> tuple[SafetyCase, ...]:
    case_path = Path(path)
    if not case_path.exists():
        LOGGER.warning("CBR 케이스 파일을 찾지 못했습니다: %s. 기본 케이스를 사용합니다", path)
        return load_default_cases()

    with case_path.open("r", encoding="utf-8") as file:
        raw_cases = json.load(file)

    if not isinstance(raw_cases, list):
        raise ValueError(f"Case library must be a JSON list: {path}")

    imported = tuple(
        _json_item_to_case(index, item)
        for index, item in enumerate(raw_cases, start=1)
        if isinstance(item, dict)
    )
    if not imported:
        LOGGER.warning("CBR 케이스 파일이 비어 있습니다. 기본 케이스를 사용합니다")
        return load_default_cases()

    LOGGER.info("CBR 케이스 %s개를 불러왔습니다: %s", len(imported), path)
    return imported
