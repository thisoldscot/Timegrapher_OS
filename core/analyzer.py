"""MetricsAnalyzer — turns a stream of BeatEvents into the four watch metrics.

Pure Python (uses only the stdlib `statistics`/`math`), so it runs unchanged on
desktop and mobile. The math is documented in DESIGN.md §4; the short version:

  rate (s/day)   slope of phase error e_n = t_n - n*(3600/bph) against time
  beat error ms  asymmetry between tick→tock and tock→tick half-swings
  amplitude °    A = (lift/2) / sin(pi * dt * bph / 7200)
  bph            median inter-beat interval, snapped to a standard train

All fits use a median-absolute-deviation (MAD) outlier reject so a single
mis-detected beat does not throw the readout.
"""
from __future__ import annotations

import math
import statistics
from collections import deque
from dataclasses import dataclass

from .beat_event import BeatEvent
from .bph_detector import detect_bph
from .constants import (
    DEFAULT_LIFT_ANGLE,
    DEFAULT_WINDOW_SECONDS,
    MIN_BEATS_FOR_METRICS,
    SECONDS_PER_DAY,
    bph_to_nominal_interval,
)


@dataclass(frozen=True)
class Metrics:
    """A computed snapshot. NaN fields mean "not enough data yet"."""
    rate_s_per_day: float
    beat_error_ms: float
    amplitude_deg: float
    bph: float
    raw_bph: float
    bph_locked: bool
    beats_in_window: int
    confidence: float       # 0..1, how consistent the window is

    @property
    def valid(self) -> bool:
        return not math.isnan(self.rate_s_per_day)


_NAN = float("nan")
_EMPTY = Metrics(_NAN, _NAN, _NAN, _NAN, _NAN, False, 0, 0.0)


def _mad_filter(values, k: float = 3.5):
    """Return values within k MADs of the median (robust outlier reject)."""
    if len(values) < 3:
        return list(values)
    med = statistics.median(values)
    mad = statistics.median([abs(v - med) for v in values]) or 1e-12
    return [v for v in values if abs(v - med) / mad <= k]


def _linfit(xs, ys):
    """Ordinary least squares slope/intercept. Returns (slope, intercept)."""
    n = len(xs)
    mx = sum(xs) / n
    my = sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    if sxx == 0:
        return 0.0, my
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    slope = sxy / sxx
    return slope, my - slope * mx


class MetricsAnalyzer:
    """Sliding-window analyzer. Feed it BeatEvents; read metrics on demand."""

    def __init__(self, *, lift_angle: float = DEFAULT_LIFT_ANGLE,
                 window_seconds: float = DEFAULT_WINDOW_SECONDS,
                 bph_mode="auto"):
        self.lift_angle = lift_angle
        self.window_seconds = window_seconds
        # bph_mode: "auto" to detect, or an int to pin the train rate.
        self.bph_mode = bph_mode
        self._beats: deque[BeatEvent] = deque()
        self._t0: float | None = None   # onset_s of the first retained beat

    # -- configuration --------------------------------------------------
    def set_lift_angle(self, deg: float) -> None:
        self.lift_angle = deg

    def set_bph_mode(self, mode) -> None:
        self.bph_mode = mode

    def reset(self) -> None:
        self._beats.clear()
        self._t0 = None

    # -- ingestion ------------------------------------------------------
    def add_beat(self, ev: BeatEvent) -> None:
        self._beats.append(ev)
        self._trim()

    def _trim(self) -> None:
        if not self._beats:
            self._t0 = None
            return
        newest = self._beats[-1].onset_s
        cutoff = newest - self.window_seconds
        while len(self._beats) > 2 and self._beats[0].onset_s < cutoff:
            self._beats.popleft()
        self._t0 = self._beats[0].onset_s

    # -- computation ----------------------------------------------------
    def compute(self) -> Metrics:
        beats = list(self._beats)
        if len(beats) < MIN_BEATS_FOR_METRICS:
            return _EMPTY

        onsets = [b.onset_s for b in beats]

        # --- BPH ---
        if isinstance(self.bph_mode, (int, float)) and self.bph_mode > 0:
            bph, raw_bph, locked = float(self.bph_mode), _NAN, True
            det = detect_bph(onsets, snap=False)
            if det:
                raw_bph = det[1]
        else:
            det = detect_bph(onsets, snap=True)
            if det is None:
                return _EMPTY
            bph, raw_bph, locked = det

        nominal = bph_to_nominal_interval(bph)

        # --- assign beat indices relative to first beat, then phase error ---
        t0 = onsets[0]
        idx, phase, ts = [], [], []
        for t in onsets:
            n = round((t - t0) / nominal)
            idx.append(n)
            phase.append((t - t0) - n * nominal)   # residual phase error
            ts.append(t - t0)

        # --- rate: slope of phase error vs time (robust paper-tape slope) ---
        keep = set(range(len(phase)))
        good_phase = _mad_filter(phase)
        if good_phase:
            lo, hi = min(good_phase), max(good_phase)
            keep = {i for i, p in enumerate(phase) if lo <= p <= hi}
        fx = [ts[i] for i in sorted(keep)]
        fy = [phase[i] for i in sorted(keep)]
        slope, _ = _linfit(fx, fy) if len(fx) >= 2 else (0.0, 0.0)
        rate = -slope * SECONDS_PER_DAY   # +ve = running fast

        # --- beat error: vertical gap between the two tape lines ---
        # The two half-swings (even/odd beat indices) sit at distinct phase
        # offsets; beat error is the separation between their detrended means.
        # Detrend by the rate slope first so a fast/slow watch does not bleed
        # into the figure (the intercept cancels in the difference).
        even_ph = _mad_filter([phase[i] - slope * ts[i] for i in range(len(phase)) if idx[i] % 2 == 0])
        odd_ph = _mad_filter([phase[i] - slope * ts[i] for i in range(len(phase)) if idx[i] % 2 == 1])
        if even_ph and odd_ph:
            beat_error = abs(statistics.mean(even_ph) - statistics.mean(odd_ph)) * 1000.0
        else:
            beat_error = _NAN

        # --- amplitude: median intra-beat dt through the lift-angle model ---
        dts = [b.dt_s for b in beats if b.dt_ticks > 0]
        dts = _mad_filter(dts)
        if dts:
            dt = statistics.median(dts)
            arg = math.pi * dt * bph / 7200.0
            s = math.sin(arg)
            amplitude = (self.lift_angle / 2.0) / s if 0 < s < 1 else _NAN
        else:
            amplitude = _NAN

        # --- confidence: interval consistency over the window ---
        all_iv = [b - a for a, b in zip(onsets, onsets[1:])]
        if len(all_iv) >= 2 and statistics.mean(all_iv) > 0:
            cv = statistics.pstdev(all_iv) / statistics.mean(all_iv)
            confidence = max(0.0, min(1.0, 1.0 - cv * 20.0))
        else:
            confidence = 0.0

        return Metrics(
            rate_s_per_day=rate,
            beat_error_ms=beat_error,
            amplitude_deg=amplitude,
            bph=bph,
            raw_bph=raw_bph,
            bph_locked=locked,
            beats_in_window=len(beats),
            confidence=confidence,
        )

    # -- helpers for the paper-tape view --------------------------------
    def tape_points(self, bph: float):
        """Yield (time_s, phase_error_s, parity) for the retained beats.

        Used by the scrolling paper-tape widget: the slope of these points is
        the rate, the vertical split between the two parity groups is the beat
        error. Returns [] if BPH is unknown.
        """
        beats = list(self._beats)
        if len(beats) < 2 or bph <= 0:
            return []
        nominal = bph_to_nominal_interval(bph)
        t0 = beats[0].onset_s
        out = []
        for b in beats:
            t = b.onset_s - t0
            n = round(t / nominal)
            out.append((b.onset_s, t - n * nominal, n % 2))
        return out
