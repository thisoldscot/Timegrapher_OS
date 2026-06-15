"""Wire/value types exchanged with the ESP32.

These are the canonical events the analyzer consumes. They are deliberately
plain dataclasses (no Tk, no numpy) so they cross the link layer, the analyzer,
the historian, and any UI unchanged.
"""
from __future__ import annotations

from dataclasses import dataclass

from .constants import DS3231_TICKS_PER_SEC


@dataclass(frozen=True)
class BeatEvent:
    """A single detected beat, timestamped against the DS3231 32 kHz clock.

    Attributes:
        seq:         monotonically increasing beat counter from the firmware.
        onset_ticks: beat onset time in DS3231 32 kHz ticks (the canonical
                     time base — divide by 32768 for seconds).
        dt_ticks:    time between the two impulse noises *within* this beat,
                     in DS3231 ticks. Feeds the amplitude formula. 0 = unresolved.
        level:       peak envelope level of the beat (0–65535), for gain/health.
    """
    seq: int
    onset_ticks: int
    dt_ticks: int
    level: int

    @property
    def onset_s(self) -> float:
        return self.onset_ticks / DS3231_TICKS_PER_SEC

    @property
    def dt_s(self) -> float:
        return self.dt_ticks / DS3231_TICKS_PER_SEC


@dataclass(frozen=True)
class WaveformChunk:
    """A decimated envelope block for the oscilloscope view (optional stream)."""
    start_ticks: int
    sample_rate: int        # decimated rate, e.g. 8000 Hz
    samples: tuple          # tuple[int, ...] envelope magnitudes


@dataclass(frozen=True)
class DeviceStatus:
    """Periodic health frame from the firmware."""
    gain: int
    clock_locked: bool      # PCNT seeing a healthy 32 kHz edge stream
    temperature_c: float    # DS3231 on-die temperature
    sample_rate: int        # measured (disciplined) audio sample rate
