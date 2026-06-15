"""TrendChart — a lightweight scrolling line plot on a tk.Canvas.

No matplotlib dependency (same spirit as the paper-tape widget): one series,
auto-scaled Y with a little headroom, an optional target band, gridlines and a
current-value readout. Feed it parallel time/value lists; NaNs are skipped.
"""
from __future__ import annotations

import math
import tkinter as tk

from ui.theme import (
    BG_CARD, CANVAS_BG, BORDER_DARK, TXT_PRIMARY, TXT_SECONDARY,
)

_PAD_L = 52
_PAD_R = 12
_PAD_T = 22
_PAD_B = 18


class TrendChart(tk.Canvas):
    def __init__(self, parent, title: str, units: str, color: str,
                 band: tuple[float, float] | None = None, height: int = 150):
        super().__init__(parent, bg=CANVAS_BG, highlightthickness=0, height=height)
        self.title = title
        self.units = units
        self.color = color
        self.band = band
        self.show_average = False
        self._times: list[float] = []
        self._values: list[float] = []
        self.bind("<Configure>", lambda _e: self.redraw())

    def set_series(self, times, values) -> None:
        self._times = list(times)
        self._values = list(values)
        self.redraw()

    def set_show_average(self, on: bool) -> None:
        self.show_average = bool(on)
        self.redraw()

    def _fmt(self, v: float) -> str:
        sign = "+" if self.units == "s/d" else ""
        return f"{v:{sign}.1f} {self.units}"

    def redraw(self) -> None:
        self.delete("all")
        w = self.winfo_width()
        h = self.winfo_height()
        if w < 60 or h < 40:
            return
        x0, x1 = _PAD_L, w - _PAD_R
        y0, y1 = _PAD_T, h - _PAD_B

        pts = [(t, v) for t, v in zip(self._times, self._values)
               if v is not None and not math.isnan(v)]

        # title + latest value
        self.create_text(x0, 10, anchor="w", text=self.title.upper(),
                         fill=TXT_SECONDARY, font=("Helvetica", 9, "bold"))
        if pts:
            latest = pts[-1][1]
            self.create_text(x1, 10, anchor="e", text=self._fmt(latest),
                             fill=self.color, font=("Consolas", 11, "bold"))

        if len(pts) < 2:
            self.create_text((x0 + x1) / 2, (y0 + y1) / 2, text="waiting for data…",
                             fill=TXT_SECONDARY, font=("Helvetica", 10))
            return

        ts = [p[0] for p in pts]
        vs = [p[1] for p in pts]
        tmin, tmax = ts[0], ts[-1]
        vmin, vmax = min(vs), max(vs)
        if self.band:
            vmin, vmax = min(vmin, self.band[0]), max(vmax, self.band[1])
        if vmax - vmin < 1e-9:
            vmin, vmax = vmin - 1, vmax + 1
        pad = (vmax - vmin) * 0.12
        vmin, vmax = vmin - pad, vmax + pad
        tspan = (tmax - tmin) or 1.0

        def sx(t):
            return x0 + (t - tmin) / tspan * (x1 - x0)

        def sy(v):
            return y1 - (v - vmin) / (vmax - vmin) * (y1 - y0)

        # target band
        if self.band:
            by0, by1 = sy(self.band[1]), sy(self.band[0])
            self.create_rectangle(x0, by0, x1, by1, fill="#203020", outline="")

        # y gridlines + labels (min / mid / max)
        for frac in (0.0, 0.5, 1.0):
            v = vmin + frac * (vmax - vmin)
            y = sy(v)
            self.create_line(x0, y, x1, y, fill=BORDER_DARK)
            self.create_text(x0 - 6, y, anchor="e", text=f"{v:.0f}",
                             fill=TXT_SECONDARY, font=("Consolas", 9))

        # the trace
        flat = []
        for t, v in pts:
            flat.extend((sx(t), sy(v)))
        self.create_line(*flat, fill=self.color, width=2, smooth=True)
        self.create_oval(flat[-2] - 3, flat[-1] - 3, flat[-2] + 3, flat[-1] + 3,
                         fill=self.color, outline="")

        # average line (dashed) across the plotted window
        if self.show_average:
            avg = sum(vs) / len(vs)
            if vmin <= avg <= vmax:
                ya = sy(avg)
                self.create_line(x0, ya, x1, ya, fill=self.color, dash=(5, 3))
                self.create_text(x0 + 4, ya - 8, anchor="w",
                                 text=f"avg {self._fmt(avg)}", fill=self.color,
                                 font=("Consolas", 9, "bold"))
