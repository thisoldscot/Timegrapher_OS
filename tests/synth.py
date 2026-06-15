"""Synthetic beat generator shared by the analyzer tests.

Produces a deterministic BeatEvent stream with known rate / beat error /
amplitude so the analyzer's outputs can be checked against ground truth.
"""
import math

from core.beat_event import BeatEvent
from core.constants import DS3231_TICKS_PER_SEC, bph_to_nominal_interval


def make_beats(*, bph=28800, rate_s_per_day=0.0, beat_error_ms=0.0,
               amplitude_deg=270.0, lift_angle=52.0, duration_s=8.0, jitter_ms=0.0,
               seed=1):
    import random
    rng = random.Random(seed)

    nominal = bph_to_nominal_interval(bph)
    actual = nominal * (1.0 - rate_s_per_day / 86400.0)
    half_be = (beat_error_ms / 1000.0) / 2.0

    arg = min(1.0, (lift_angle / 2.0) / max(amplitude_deg, 1e-6))
    dt_s = (7200.0 / (math.pi * bph)) * math.asin(arg)
    dt_ticks = max(1, int(round(dt_s * DS3231_TICKS_PER_SEC)))

    beats = []
    seq = 0
    t = 0.0
    while t < duration_s:
        be = half_be if seq % 2 == 0 else -half_be
        jitter = rng.gauss(0.0, jitter_ms / 1000.0)
        onset = t + be + jitter
        beats.append(BeatEvent(
            seq=seq,
            onset_ticks=int(round(onset * DS3231_TICKS_PER_SEC)),
            dt_ticks=dt_ticks,
            level=30000,
        ))
        seq += 1
        t += actual
    return beats
