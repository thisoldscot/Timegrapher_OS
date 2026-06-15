"""MockLink — synthetic beat generator for UI development and tests.

Produces a realistic BeatEvent stream with configurable rate offset, beat error,
amplitude, and jitter, timestamped on a simulated DS3231 32 kHz clock. Lets the
entire app run with no hardware attached.
"""
from __future__ import annotations

import math
import random
import threading
import time

from core.beat_event import BeatEvent, DeviceStatus, WaveformChunk
from core.constants import DS3231_TICKS_PER_SEC, bph_to_nominal_interval

from .base_link import BaseLink

# Decimated envelope stream for the scope view (mirrors firmware WAVE output).
_WAVE_SR = 8000                      # decimated samples/sec
_WAVE_PRE_MS = 4.0                   # window starts this long before the beat
_WAVE_SPAN_MS = 28.0                 # total window length


class MockLink(BaseLink):
    def __init__(self, *, bph: int = 28800, rate_s_per_day: float = 4.0,
                 beat_error_ms: float = 0.3, amplitude_deg: float = 275.0,
                 lift_angle: float = 52.0, jitter_ms: float = 0.15):
        self.bph = bph
        self.rate_s_per_day = rate_s_per_day
        self.beat_error_ms = beat_error_ms
        self.amplitude_deg = amplitude_deg
        self.lift_angle = lift_angle
        self.jitter_ms = jitter_ms
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._open = False
        self._waveform = False

    @property
    def is_open(self) -> bool:
        return self._open

    def open(self) -> None:
        if self._open:
            return
        self._stop.clear()
        self._open = True
        self._thread = threading.Thread(target=self._run, name="MockLink", daemon=True)
        self._thread.start()

    def close(self) -> None:
        self._stop.set()
        self._open = False
        if self._thread:
            self._thread.join(timeout=1.0)
            self._thread = None

    def subscribe_waveform(self, enabled: bool) -> None:
        self._waveform = bool(enabled)

    # -- synthetic generation -------------------------------------------
    def _envelope_for_beat(self, dt_s: float, level: int) -> tuple:
        """Build a decimated envelope for one beat: the escapement's two/three
        impulse noises (unlocking, impulse, drop) as fast-attack / exp-decay
        spikes. dt_s is the gap between the two main impulses (amplitude)."""
        n = int(round(_WAVE_SPAN_MS / 1000.0 * _WAVE_SR))
        buf = [0.0] * n
        peak = max(1, level)
        # (offset from window start in ms, relative height, decay time-const ms)
        spikes = [
            (_WAVE_PRE_MS, 0.85, 0.6),                       # unlocking
            (_WAVE_PRE_MS + dt_s * 1000.0, 1.00, 0.7),       # impulse
            (_WAVE_PRE_MS + dt_s * 1000.0 + 1.6, 0.45, 0.5),  # drop
        ]
        for j in range(n):
            t_ms = j * 1000.0 / _WAVE_SR
            v = 0.0
            for at, h, tau in spikes:
                if t_ms >= at:
                    v += h * peak * math.exp(-(t_ms - at) / tau)
            v += random.gauss(0.0, peak * 0.015)             # noise floor
            buf[j] = v
        return tuple(min(65535, max(0, int(s))) for s in buf)

    def _dt_ticks_for_amplitude(self) -> int:
        """Invert the amplitude formula to get the intra-beat dt the firmware
        would have measured for the configured amplitude."""
        # A = (L/2)/sin(pi*dt*bph/7200)  ->  dt = (7200/(pi*bph)) * asin(L/(2A))
        arg = (self.lift_angle / 2.0) / max(self.amplitude_deg, 1e-6)
        arg = min(1.0, max(0.0, arg))
        dt_s = (7200.0 / (math.pi * self.bph)) * math.asin(arg)
        return int(round(dt_s * DS3231_TICKS_PER_SEC))

    def _run(self) -> None:
        nominal = bph_to_nominal_interval(self.bph)
        # A fast watch advances: actual interval shrinks by the daily fraction.
        gain = self.rate_s_per_day / 86400.0
        actual = nominal * (1.0 - gain)
        half_be = (self.beat_error_ms / 1000.0) / 2.0
        dt_ticks = self._dt_ticks_for_amplitude()

        seq = 0
        sim_time = 0.0           # simulated DS3231 seconds
        wall_start = time.monotonic()
        next_wall = wall_start

        while not self._stop.is_set():
            # Alternate half-swings carry +/- the beat-error offset.
            be = half_be if (seq % 2 == 0) else -half_be
            jitter = random.gauss(0.0, self.jitter_ms / 1000.0)
            onset = sim_time + be + jitter
            onset_ticks = int(round(onset * DS3231_TICKS_PER_SEC))
            this_dt = max(1, dt_ticks + random.randint(-3, 3))
            level = random.randint(20000, 40000)
            self._emit_beat(BeatEvent(
                seq=seq, onset_ticks=onset_ticks, dt_ticks=this_dt, level=level))

            if self._waveform:
                start_ticks = onset_ticks - int(round(
                    _WAVE_PRE_MS / 1000.0 * DS3231_TICKS_PER_SEC))
                self._emit_waveform(WaveformChunk(
                    start_ticks=start_ticks, sample_rate=_WAVE_SR,
                    samples=self._envelope_for_beat(
                        this_dt / DS3231_TICKS_PER_SEC, level)))
            if seq % 64 == 0:
                self._emit_status(DeviceStatus(
                    gain=32, clock_locked=True, temperature_c=25.0,
                    sample_rate=48000))

            seq += 1
            sim_time += actual
            next_wall += actual
            sleep = next_wall - time.monotonic()
            if sleep > 0:
                self._stop.wait(sleep)
