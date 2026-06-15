"""Abstract base class for every ESP32 transport.

To add a new transport:
  1. Create links/<name>.py implementing BaseLink
  2. Register it in links/link_manager.py

A link runs its own reader thread and calls the supplied callbacks. It must
never touch the UI directly — callbacks are invoked off the main thread, so the
UI is responsible for marshalling back (a queue drained on an after() tick).
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Callable

from core.beat_event import BeatEvent, DeviceStatus, WaveformChunk

OnBeat = Callable[[BeatEvent], None]
OnStatus = Callable[[DeviceStatus], None]
OnWaveform = Callable[[WaveformChunk], None]


class BaseLink(ABC):
    """Common interface every ESP32 transport must implement."""

    @abstractmethod
    def open(self) -> None:
        """Open the transport and start the reader thread. Raise on failure."""

    @abstractmethod
    def close(self) -> None:
        """Stop the reader thread and release the transport. Must not raise."""

    @property
    @abstractmethod
    def is_open(self) -> bool:
        ...

    def set_callbacks(self, *, on_beat: OnBeat | None = None,
                      on_status: OnStatus | None = None,
                      on_waveform: OnWaveform | None = None) -> None:
        self._on_beat = on_beat
        self._on_status = on_status
        self._on_waveform = on_waveform

    # -- commands to the device (no-op default; serial/wifi override) ----
    def set_gain(self, gain: int) -> None:
        ...

    def subscribe_waveform(self, enabled: bool) -> None:
        ...

    def ping(self) -> None:
        ...

    # -- helpers for subclasses -----------------------------------------
    _on_beat: OnBeat | None = None
    _on_status: OnStatus | None = None
    _on_waveform: OnWaveform | None = None

    def _emit_beat(self, ev: BeatEvent) -> None:
        if self._on_beat:
            self._on_beat(ev)

    def _emit_status(self, st: DeviceStatus) -> None:
        if self._on_status:
            self._on_status(st)

    def _emit_waveform(self, wf: WaveformChunk) -> None:
        if self._on_waveform:
            self._on_waveform(wf)
