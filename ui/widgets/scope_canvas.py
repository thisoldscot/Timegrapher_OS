"""ScopeCanvas — a trigger-aligned oscilloscope for the beat envelope.

Fed decimated envelope chunks (WaveformChunk: samples + sample_rate). Each chunk
is one beat's acoustic signature — the escapement's unlocking / impulse / drop
noises. Like a hardware scope it triggers on the rising edge of the envelope so
successive beats overlay on the same time origin; a short persistence trail keeps
the previous few sweeps faintly visible. The time axis is milliseconds relative
to the trigger; the two main spikes' spacing is the amplitude information.
"""
from __future__ import annotations

import tkinter as tk
from collections import deque

from ui.theme import (
    CANVAS_BG, CANVAS_GRID_MAJOR, CANVAS_GRID_MINOR, BORDER_LIGHT,
    BRAND_CYAN, TXT_SECONDARY, TXT_PRIMARY,
)

_TRIG_FRAC = 0.15      # trigger sits 15% from the left edge
_PERSIST = 5           # sweeps kept on screen (newest brightest)
_PAD = 10
_BASE_PAD = 16         # room for the ms axis labels
# Dim → bright trail (oldest first, newest last == BRAND_CYAN).
_TRAIL = ("#0e3b44", "#13525e", "#1a6f7e", "#1f8a9c", BRAND_CYAN)


class ScopeCanvas(tk.Canvas):
    def __init__(self, parent):
        super().__init__(parent, bg=CANVAS_BG, highlightthickness=0, bd=0)
        self._frames: deque = deque(maxlen=_PERSIST)   # each: (samples, sr)
        self._gain = 8000.0
        self.bind("<Configure>", lambda _e: self.redraw())

    def reset(self) -> None:
        self._frames.clear()
        self.delete("all")

    def push(self, samples, sample_rate: int) -> None:
        if not samples:
            return
        self._frames.append((tuple(samples), sample_rate))
        # Slow-tracking auto-gain so spikes fill the screen without clipping flicker.
        peak = max(max(f[0]) for f in self._frames)
        self._gain = max(self._gain * 0.8 + peak * 0.2, 1000.0)
        self.redraw()

    # -- drawing -------------------------------------------------------
    @staticmethod
    def _trigger_index(samples) -> int:
        thresh = max(samples) * 0.4
        for i, s in enumerate(samples):
            if s >= thresh:
                return i
        return 0

    def redraw(self) -> None:
        self.delete("all")
        w = self.winfo_width()
        h = self.winfo_height()
        if w < 40 or h < 40:
            return

        base = h - _BASE_PAD
        top = _PAD
        amp_h = base - top
        trig_x = w * _TRIG_FRAC

        if not self._frames:
            self.create_text(w / 2, h / 2, text="Waiting for envelope…\n"
                             "(streams while the Scope is open)",
                             fill=TXT_SECONDARY, font=("Helvetica", 11),
                             justify="center")
            return

        sr = self._frames[-1][1]
        n = len(self._frames[-1][0])
        dx = (w - 2 * _PAD) / max(1, n)            # px per sample
        px_per_ms = dx * sr / 1000.0

        self._draw_grid(w, base, top, trig_x, px_per_ms)

        # Oldest → newest so the bright sweep lands on top.
        ncolors = len(_TRAIL)
        start = ncolors - len(self._frames)
        for idx, (samples, fsr) in enumerate(self._frames):
            color = _TRAIL[min(ncolors - 1, start + idx)]
            ti = self._trigger_index(samples)
            flat = []
            for j, s in enumerate(samples):
                x = trig_x + (j - ti) * dx
                if x < 0 or x > w:
                    continue
                y = base - min(1.0, s / self._gain) * amp_h
                flat.extend((x, y))
            if len(flat) >= 4:
                width = 2 if idx == len(self._frames) - 1 else 1
                self.create_line(*flat, fill=color, width=width)

        self.create_text(_PAD, 12, anchor="w", text="ENVELOPE",
                         fill=TXT_SECONDARY, font=("Helvetica", 9, "bold"))
        self.create_text(w - _PAD, 12, anchor="e",
                         text=f"{sr / 1000:.0f} kHz · {n} pts",
                         fill=TXT_SECONDARY, font=("Consolas", 9))

    def _draw_grid(self, w, base, top, trig_x, px_per_ms) -> None:
        # Vertical ms gridlines every 1 ms (5 ms major), 0 ms = the trigger.
        ms = 0
        while True:                          # rightward from the trigger
            x = trig_x + ms * px_per_ms
            if x > w:
                break
            self._vline(x, top, base, ms, major=(ms % 5 == 0))
            ms += 1
        ms = -1
        while True:                          # leftward (pre-trigger)
            x = trig_x + ms * px_per_ms
            if x < 0:
                break
            self._vline(x, top, base, ms, major=(ms % 5 == 0))
            ms -= 1
        self.create_line(_PAD, base, w - _PAD, base, fill=CANVAS_GRID_MAJOR)
        # Bright trigger line.
        self.create_line(trig_x, top, trig_x, base, fill=BORDER_LIGHT, width=2)

    def _vline(self, x, top, base, ms, major) -> None:
        self.create_line(x, top, x, base,
                         fill=CANVAS_GRID_MAJOR if major else CANVAS_GRID_MINOR,
                         dash=(2, 4))
        if major:
            self.create_text(x, base + 8, text=f"{ms:+d}", fill=TXT_SECONDARY,
                             font=("Consolas", 7))
