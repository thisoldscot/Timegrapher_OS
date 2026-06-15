"""Ground-truth checks: synthetic beats with known metrics → analyzer output."""
import math

from core.analyzer import MetricsAnalyzer

from .synth import make_beats


def _run(beats, lift_angle=52.0, bph_mode="auto"):
    a = MetricsAnalyzer(lift_angle=lift_angle, window_seconds=10.0, bph_mode=bph_mode)
    for b in beats:
        a.add_beat(b)
    return a.compute()


def test_perfect_watch_reads_near_zero():
    m = _run(make_beats(rate_s_per_day=0.0, beat_error_ms=0.0, amplitude_deg=270.0))
    assert m.valid
    assert m.bph == 28800
    assert abs(m.rate_s_per_day) < 0.5
    assert m.beat_error_ms < 0.1
    assert abs(m.amplitude_deg - 270.0) < 3.0


def test_known_rate_offset():
    m = _run(make_beats(rate_s_per_day=12.0, amplitude_deg=260.0))
    assert abs(m.rate_s_per_day - 12.0) < 1.0


def test_negative_rate():
    m = _run(make_beats(rate_s_per_day=-8.0))
    assert abs(m.rate_s_per_day - (-8.0)) < 1.0


def test_beat_error_recovered():
    m = _run(make_beats(beat_error_ms=0.8))
    assert abs(m.beat_error_ms - 0.8) < 0.15


def test_amplitude_recovered():
    m = _run(make_beats(amplitude_deg=290.0, lift_angle=52.0), lift_angle=52.0)
    assert abs(m.amplitude_deg - 290.0) < 4.0


def test_lift_angle_changes_amplitude():
    beats = make_beats(amplitude_deg=270.0, lift_angle=52.0)
    m48 = _run(beats, lift_angle=48.0)
    m52 = _run(beats, lift_angle=52.0)
    # Larger lift angle reads a larger amplitude for the same dt.
    assert m52.amplitude_deg > m48.amplitude_deg


def test_pinned_bph():
    m = _run(make_beats(bph=21600, rate_s_per_day=5.0), bph_mode=21600)
    assert m.bph == 21600
    assert abs(m.rate_s_per_day - 5.0) < 1.0


def test_bph_autodetect_36000():
    m = _run(make_beats(bph=36000, amplitude_deg=300.0))
    assert m.bph == 36000


def test_jitter_tolerated():
    m = _run(make_beats(rate_s_per_day=6.0, jitter_ms=0.2, duration_s=12.0))
    assert abs(m.rate_s_per_day - 6.0) < 2.0


def test_insufficient_data_is_invalid():
    a = MetricsAnalyzer()
    for b in make_beats(duration_s=0.05):
        a.add_beat(b)
    assert not a.compute().valid
