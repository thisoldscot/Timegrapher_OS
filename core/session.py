"""Measurement session model — positions and their captured metrics.

A session is one watch on the bench. The watchmaker measures it in several
positions (dial up/down, crown up/down, etc.); each position holds the metrics
snapshot taken there. Position deltas drive the regulation analysis.
"""
from __future__ import annotations

import math
import time
from dataclasses import dataclass, field

# Canonical measurement positions and their conventional abbreviations.
POSITIONS = [
    ("DU", "Dial Up"),
    ("DD", "Dial Down"),
    ("CU", "Crown Up"),
    ("CD", "Crown Down"),
    ("CL", "Crown Left (6 up)"),
    ("CR", "Crown Right (12 up)"),
]


@dataclass
class PositionResult:
    code: str
    rate_s_per_day: float
    beat_error_ms: float
    amplitude_deg: float
    captured_at: float = field(default_factory=time.time)


@dataclass
class Session:
    watch_name: str = ""
    movement_label: str = ""
    bph: int = 28800
    lift_angle: float = 52.0
    notes: str = ""
    started_at: float = field(default_factory=time.time)
    results: dict[str, PositionResult] = field(default_factory=dict)

    def record(self, code: str, metrics) -> None:
        """Store a Metrics snapshot for a position code."""
        self.results[code] = PositionResult(
            code=code,
            rate_s_per_day=metrics.rate_s_per_day,
            beat_error_ms=metrics.beat_error_ms,
            amplitude_deg=metrics.amplitude_deg,
        )

    def rate_delta(self) -> float | None:
        """Max−min rate across measured positions (the regulation spread)."""
        rates = [r.rate_s_per_day for r in self.results.values()]
        return (max(rates) - min(rates)) if len(rates) >= 2 else None

    def amplitude_delta(self) -> float | None:
        amps = [r.amplitude_deg for r in self.results.values()]
        return (max(amps) - min(amps)) if len(amps) >= 2 else None

    def averages(self) -> dict[str, float | None]:
        """Mean rate / amplitude / beat error across captured positions.

        NaN readings (e.g. amplitude when no intra-beat impulse was resolved)
        are excluded per-metric, so a missing amplitude never poisons the rate
        mean. Returns None for a metric with no valid values.
        """
        def mean(vals):
            clean = [v for v in vals if v is not None and not math.isnan(v)]
            return (sum(clean) / len(clean)) if clean else None

        rs = self.results.values()
        return {
            "rate_s_per_day": mean([r.rate_s_per_day for r in rs]),
            "amplitude_deg": mean([r.amplitude_deg for r in rs]),
            "beat_error_ms": mean([r.beat_error_ms for r in rs]),
        }
