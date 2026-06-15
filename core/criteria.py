"""Pass/fail criteria for positional measurements.

Tk-free and dependency-free so the UI, the PDF report and any future mobile
build share one definition of "good". A reading is judged on up to four axes:

  * rate        — within ``rate_target`` ± ``rate_tol`` (s/d)
  * beat error  — at or below ``be_max`` (ms); it is reported as a magnitude
  * amplitude   — inside [``amp_min``, ``amp_max``] (°)
  * rate spread — max−min rate across positions ≤ ``spread_max`` (s/d), the
                  regulation/poise quality of the whole run

A metric that was not measured (None / NaN — e.g. amplitude with no resolved
impulse) is reported as ``None`` and never counts as a failure on its own.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

# Default tolerances. Deliberately "good general service" grade rather than
# chronometer-tight; every value is adjustable from Settings.
DEFAULT_CRITERIA = {
    "tol_rate_target": 0.0,    # s/d the watch is being regulated toward
    "tol_rate": 10.0,          # ± s/d allowed per position
    "tol_be_max": 0.5,         # ms, maximum beat error
    "tol_amp_min": 200.0,      # ° minimum healthy amplitude
    "tol_amp_max": 320.0,      # ° maximum (over-banking guard)
    "tol_spread": 12.0,        # s/d, maximum rate spread across positions
}


def _ok(v) -> bool:
    return v is not None and not (isinstance(v, float) and math.isnan(v))


@dataclass
class Criteria:
    rate_target: float = 0.0
    rate_tol: float = 10.0
    be_max: float = 0.5
    amp_min: float = 200.0
    amp_max: float = 320.0
    spread_max: float = 12.0

    @classmethod
    def from_settings(cls, store) -> "Criteria":
        g = store.get
        return cls(
            rate_target=float(g("tol_rate_target", 0.0)),
            rate_tol=float(g("tol_rate", 10.0)),
            be_max=float(g("tol_be_max", 0.5)),
            amp_min=float(g("tol_amp_min", 200.0)),
            amp_max=float(g("tol_amp_max", 320.0)),
            spread_max=float(g("tol_spread", 12.0)),
        )

    # -- per-metric checks (None = not measured) ----------------------
    def check_rate(self, rate):
        return abs(rate - self.rate_target) <= self.rate_tol if _ok(rate) else None

    def check_beat_error(self, be):
        return be <= self.be_max if _ok(be) else None

    def check_amplitude(self, amp):
        return self.amp_min <= amp <= self.amp_max if _ok(amp) else None


def _field(r, name):
    """Read a metric from either a dataclass (attr) or a dict (key)."""
    if isinstance(r, dict):
        return r.get(name)
    return getattr(r, name, None)


def evaluate_reading(rate, amp, be, criteria: Criteria) -> dict:
    """Per-position verdict. 'pass' is None when nothing measurable was present."""
    checks = {
        "rate": criteria.check_rate(rate),
        "amplitude": criteria.check_amplitude(amp),
        "beat_error": criteria.check_beat_error(be),
    }
    measured = [v for v in checks.values() if v is not None]
    return {"checks": checks, "pass": (all(measured) if measured else None)}


def evaluate_session(results: dict, criteria: Criteria) -> dict:
    """Evaluate every captured position plus the across-position rate spread.

    Overall passes only if every measured position passes *and* the spread is
    within tolerance. Returns per-code verdicts, the spread and its verdict.
    """
    per = {}
    rates = []
    for code, r in results.items():
        rate = _field(r, "rate_s_per_day")
        amp = _field(r, "amplitude_deg")
        be = _field(r, "beat_error_ms")
        per[code] = evaluate_reading(rate, amp, be, criteria)
        if _ok(rate):
            rates.append(rate)

    spread = (max(rates) - min(rates)) if len(rates) >= 2 else None
    spread_pass = (spread <= criteria.spread_max) if spread is not None else None

    verdicts = [p["pass"] for p in per.values() if p["pass"] is not None]
    overall = None
    if verdicts:
        overall = all(verdicts) and (spread_pass is not False)

    return {"per": per, "spread": spread, "spread_pass": spread_pass,
            "overall": overall}
