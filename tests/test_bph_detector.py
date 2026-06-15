from core.bph_detector import detect_bph
from core.constants import bph_to_nominal_interval


def _onsets(bph, n=40):
    iv = bph_to_nominal_interval(bph)
    return [i * iv for i in range(n)]


def test_detect_each_standard_rate():
    for bph in (18000, 21600, 28800, 36000):
        result = detect_bph(_onsets(bph))
        assert result is not None
        detected, raw, snapped = result
        assert detected == bph
        assert snapped


def test_too_little_data():
    assert detect_bph([0.0, 0.1]) is None


def test_no_snap_returns_raw():
    onsets = _onsets(28800)
    detected, raw, snapped = detect_bph(onsets, snap=False)
    assert not snapped
    assert abs(detected - 28800) < 50
