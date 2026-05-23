"""Weighted CBR and rule-based risk scoring."""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from server.cbr.case_library import SafetyCase, load_default_cases
from shared.config import RiskConfig
from shared.models import MonitoringPayload, RiskAssessment, RiskLevel, utc_now_iso


def _bounded_similarity(value: float, target: float, span: float) -> float:
    return max(0.0, 1.0 - min(abs(value - target) / span, 1.0))


@dataclass(slots=True)
class DeviceRiskState:
    no_helmet_started_at: float | None = None
    recent_danger_timestamps: list[float] = field(default_factory=list)


class CBREngine:
    def __init__(
        self,
        config: RiskConfig,
        cases: tuple[SafetyCase, ...] | None = None,
    ) -> None:
        self.config = config
        self.cases = cases or load_default_cases()
        self._states: dict[str, DeviceRiskState] = {}

    def assess(self, payload: MonitoringPayload) -> RiskAssessment:
        state = self._states.setdefault(payload.device_id, DeviceRiskState())
        now = time.monotonic()

        no_helmet = payload.detection.no_helmet_count > 0
        if no_helmet and state.no_helmet_started_at is None:
            state.no_helmet_started_at = now
        elif not no_helmet:
            state.no_helmet_started_at = None

        unsafe_duration = (
            now - state.no_helmet_started_at
            if state.no_helmet_started_at is not None
            else 0.0
        )
        state.recent_danger_timestamps = [
            item
            for item in state.recent_danger_timestamps
            if now - item <= self.config.repeat_window_seconds
        ]
        repeat_count = len(state.recent_danger_timestamps)

        rule_score, factors = self._rule_score(payload, unsafe_duration, repeat_count)
        matched_case, similarity = self._match_case(payload, unsafe_duration, repeat_count)
        case_score = self._risk_to_score(matched_case.expected_risk) * similarity
        risk_score = max(rule_score, case_score)
        risk_level = self._score_to_level(risk_score)

        if risk_level == RiskLevel.DANGER:
            state.recent_danger_timestamps.append(now)

        summary = self._summarize(payload, risk_level, factors, matched_case.case_id)
        return RiskAssessment(
            device_id=payload.device_id,
            timestamp=utc_now_iso(),
            risk_level=risk_level,
            risk_score=risk_score,
            matched_case_id=matched_case.case_id,
            similarity=similarity,
            event_summary=summary,
            factors=factors,
        )

    def _rule_score(
        self,
        payload: MonitoringPayload,
        unsafe_duration: float,
        repeat_count: int,
    ) -> tuple[float, dict[str, float]]:
        score = 0.0
        factors: dict[str, float] = {}
        temperature = payload.sensor.temperature_c
        noise = payload.sensor.noise_db

        if payload.detection.no_helmet_count > 0:
            factors["no_helmet"] = 42.0
            score += factors["no_helmet"]
        elif payload.detection.person_count > 0 and payload.detection.helmet_detected:
            factors["helmet_ok"] = -8.0
            score += factors["helmet_ok"]

        if temperature is not None:
            if temperature >= self.config.critical_temperature_c:
                factors["critical_temperature"] = 30.0
            elif temperature >= self.config.high_temperature_c:
                factors["high_temperature"] = 18.0
            if "critical_temperature" in factors:
                score += factors["critical_temperature"]
            elif "high_temperature" in factors:
                score += factors["high_temperature"]

        if noise is not None:
            if noise >= self.config.critical_noise_db:
                factors["critical_noise"] = 26.0
            elif noise >= self.config.loud_noise_db:
                factors["loud_noise"] = 15.0
            if "critical_noise" in factors:
                score += factors["critical_noise"]
            elif "loud_noise" in factors:
                score += factors["loud_noise"]

        if unsafe_duration >= self.config.unsafe_duration_danger_seconds:
            factors["unsafe_duration"] = 26.0
            score += factors["unsafe_duration"]
        elif unsafe_duration >= self.config.unsafe_duration_warning_seconds:
            factors["unsafe_duration"] = 14.0
            score += factors["unsafe_duration"]

        if repeat_count >= 3:
            factors["repeated_pattern"] = 18.0
            score += factors["repeated_pattern"]
        elif repeat_count >= 1:
            factors["repeated_pattern"] = 8.0
            score += factors["repeated_pattern"]

        factors["unsafe_duration_seconds"] = round(unsafe_duration, 2)
        factors["repeat_count"] = float(repeat_count)
        return max(0.0, min(score, 100.0)), factors

    def _match_case(
        self,
        payload: MonitoringPayload,
        unsafe_duration: float,
        repeat_count: int,
    ) -> tuple[SafetyCase, float]:
        temperature = payload.sensor.temperature_c if payload.sensor.temperature_c is not None else 25.0
        noise = payload.sensor.noise_db if payload.sensor.noise_db is not None else 60.0
        no_helmet_count = payload.detection.no_helmet_count

        best_case = self.cases[0]
        best_similarity = -1.0
        for case in self.cases:
            similarities = {
                "temperature": _bounded_similarity(temperature, case.temperature_c, 20.0),
                "noise": _bounded_similarity(noise, case.noise_db, 50.0),
                "helmet": 1.0
                if min(no_helmet_count, 1) == min(case.no_helmet_count, 1)
                else 0.0,
                "duration": _bounded_similarity(
                    unsafe_duration,
                    case.unsafe_duration_seconds,
                    max(10.0, self.config.unsafe_duration_danger_seconds),
                ),
                "repeat": _bounded_similarity(float(repeat_count), float(case.repeat_count), 5.0),
            }
            weighted = sum(
                similarities[name] * weight for name, weight in case.weights.items()
            )
            if weighted > best_similarity:
                best_case = case
                best_similarity = weighted

        return best_case, max(0.0, min(best_similarity, 1.0))

    def _score_to_level(self, score: float) -> RiskLevel:
        if score >= self.config.danger_threshold:
            return RiskLevel.DANGER
        if score >= self.config.warning_threshold:
            return RiskLevel.WARNING
        return RiskLevel.SAFE

    @staticmethod
    def _risk_to_score(level: RiskLevel) -> float:
        if level == RiskLevel.DANGER:
            return 85.0
        if level == RiskLevel.WARNING:
            return 55.0
        return 15.0

    @staticmethod
    def _summarize(
        payload: MonitoringPayload,
        risk_level: RiskLevel,
        factors: dict[str, float],
        case_id: str,
    ) -> str:
        parts = [f"{risk_level.value}: matched {case_id}."]
        if payload.detection.no_helmet_count > 0:
            parts.append(f"{payload.detection.no_helmet_count} no-helmet detection(s).")
        if payload.sensor.temperature_c is not None:
            parts.append(f"Temperature {payload.sensor.temperature_c:.1f}C.")
        if payload.sensor.noise_db is not None:
            parts.append(f"Noise {payload.sensor.noise_db:.1f}dB.")
        if factors.get("unsafe_duration_seconds", 0) > 0:
            parts.append(f"Unsafe duration {factors['unsafe_duration_seconds']:.1f}s.")
        return " ".join(parts)
