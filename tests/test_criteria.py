import math

from core.criteria import Criteria, evaluate_reading, evaluate_session


def _c():
    # defaults: rate ±10, beat error ≤0.5, amplitude 200–320, spread ≤12
    return Criteria()


def test_reading_passes_within_all_tolerances():
    r = evaluate_reading(5.0, 280.0, 0.3, _c())
    assert r["pass"] is True
    assert all(r["checks"].values())


def test_each_metric_fails_independently():
    c = _c()
    assert evaluate_reading(15.0, 280.0, 0.3, c)["checks"]["rate"] is False
    assert evaluate_reading(2.0, 280.0, 0.7, c)["checks"]["beat_error"] is False
    assert evaluate_reading(2.0, 190.0, 0.3, c)["checks"]["amplitude"] is False
    assert evaluate_reading(2.0, 330.0, 0.3, c)["checks"]["amplitude"] is False


def test_unmeasured_metric_is_none_not_failure():
    # NaN amplitude must not drag the position to a fail on its own.
    r = evaluate_reading(2.0, float("nan"), 0.3, _c())
    assert r["checks"]["amplitude"] is None
    assert r["pass"] is True


def test_rate_target_offset_shifts_window():
    c = Criteria(rate_target=10.0, rate_tol=5.0)   # accept 5..15 s/d
    assert c.check_rate(12.0) is True
    assert c.check_rate(2.0) is False


def test_session_overall_requires_positions_and_spread():
    c = _c()
    good = {
        "DU": {"rate_s_per_day": 2, "amplitude_deg": 285, "beat_error_ms": 0.2},
        "DD": {"rate_s_per_day": 4, "amplitude_deg": 280, "beat_error_ms": 0.3},
    }
    ev = evaluate_session(good, c)
    assert ev["overall"] is True
    assert ev["spread_pass"] is True

    # A large positional spread fails the run even when each reading is in band.
    spread = {
        "DU": {"rate_s_per_day": -8, "amplitude_deg": 285, "beat_error_ms": 0.2},
        "DD": {"rate_s_per_day": 9, "amplitude_deg": 280, "beat_error_ms": 0.3},
    }
    ev2 = evaluate_session(spread, c)
    assert ev2["spread"] == 17
    assert ev2["spread_pass"] is False
    assert ev2["overall"] is False


def test_empty_session_is_indeterminate():
    ev = evaluate_session({}, _c())
    assert ev["overall"] is None
    assert ev["spread"] is None
