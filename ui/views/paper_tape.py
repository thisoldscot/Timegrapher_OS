"""PaperTape — the signature scrolling timegrapher trace.

Each beat is a dot. Vertical axis is time (newest at top, scrolling down).
Horizontal axis is the beat's timing deviation from the ideal grid (the residual
phase error), centred on the screen.

Reading the trace, exactly like a hardware timegrapher:
  * slope of the dot-line   = rate (fast = leans one way, slow = the other)
  * the two interleaved lines (tick vs tock) = the two half-swings; the
    horizontal gap between them is the beat error.

Centering: residuals are measured against a grid anchored on the *newest* beat
and then recentred on the robust median of the visible dots. That keeps the
centre line well-defined regardless of how far the watch has drifted since the
session began (the old code anchored to the first-ever beat, so accumulated rate
drift slowly pushed the whole cluster off one side of the screen).
"""
from __future__ import annotations

import statistics
import tkinter as tk
from collections import deque

from core.constants import bph_to_nominal_interval
from ui.theme import (
    CANVAS_BG, CANVAS_GRID_MAJOR, CANVAS_GRID_MINOR, BORDER_LIGHT,
    BRAND_CYAN, SUCCESS_GREEN, TXT_SECONDARY, TXT_PRIMARY,
)


class PaperTape(tk.Canvas):
    SECONDS_VISIBLE = 5.0      # vertical span
    HALF_SPAN_MS = 10.0        # horizontal half-width in ms (zoom)
    DOT_R = 2

    def __init__(self, parent):
        super().__init__(parent, bg=CANVAS_BG, highlightthickness=0, bd=0)
        self._onsets: deque = deque(maxlen=4000)   # raw beat onset times (s)
        self._nominal: float = bph_to_nominal_interval(28800)
        self.bind("<Configure>", lambda e: self.redraw())

    def reset(self) -> None:
        self._onsets.clear()
        self.delete("all")

    def push_beat(self, onset_s: float, bph: float) -> None:
        if bph <= 0:
            return
        self._nominal = bph_to_nominal_interval(bph)
        self._onsets.append(onset_s)

    def redraw(self) -> None:
        self.delete("all")
        w = self.winfo_width()
        h = self.winfo_height()
        if w < 10 or h < 10 or not self._onsets:
            return

        cx = w / 2
        px_per_ms = (w / 2) / self.HALF_SPAN_MS
        px_per_s = h / self.SECONDS_VISIBLE
        self._draw_grid(w, h, cx, px_per_ms)

        nominal = self._nominal
        newest = self._onsets[-1]

        # Residual of each visible beat against the grid anchored on the newest
        # beat: r = (onset - newest) wrapped into ±nominal/2. Parity (tick/tock)
        # is the grid index parity, so the two half-swings land on two lines.
        visible = []
        for onset in self._onsets:
            age = newest - onset
            if age > self.SECONDS_VISIBLE:
                continue
            k = round((onset - newest) / nominal)
            residual_ms = ((onset - newest) - k * nominal) * 1000.0
            visible.append((age, residual_ms, k % 2))
        if not visible:
            return

        # Recentre on the robust median so the centre line sits between the two
        # parity lines (cancels the newest beat's own half-swing offset).
        center = statistics.median(r for _, r, _ in visible)

        r = self.DOT_R
        for age, residual_ms, parity in visible:
            x = cx + (residual_ms - center) * px_per_ms
            if x < 0 or x > w:
                continue
            y = age * px_per_s
            color = BRAND_CYAN if parity == 0 else SUCCESS_GREEN
            self.create_oval(x - r, y - r, x + r, y + r, fill=color, outline="")

    def _draw_grid(self, w, h, cx, px_per_ms) -> None:
        # Minor deviation gridlines (dashed) + labels.
        for ms in (-10, -5, -2, -1, 1, 2, 5, 10):
            x = cx + ms * px_per_ms
            if not (0 < x < w):
                continue
            major = ms in (-10, -5, 5, 10)
            self.create_line(x, 0, x, h,
                             fill=CANVAS_GRID_MAJOR if major else CANVAS_GRID_MINOR,
                             dash=(2, 4))
            if major:
                self.create_text(x, h - 8, text=f"{ms:+d}", fill=TXT_SECONDARY,
                                 font=("Consolas", 7))
        # Bright, solid centre line — the 0 ms reference.
        self.create_line(cx, 0, cx, h, fill=BORDER_LIGHT, width=2)
        self.create_text(cx, h - 8, text="0 ms", fill=TXT_PRIMARY,
                         font=("Consolas", 7, "bold"))
