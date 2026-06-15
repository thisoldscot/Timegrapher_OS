"""TrendsView — rate / amplitude / beat-error over time.

Plots the in-memory sample trail the app logs (~1/sec) while connected. The
History view can also push a saved session's samples in here for review. Three
stacked charts share the elapsed-time axis.

Time base: by default the charts span the *whole session* (every logged sample
since Connect, capped at ~1 h). The window selector trims that to the last N
seconds, reusing the same windows configured for the Live averages, so the two
views can be read against the same time base. "Show averages" overlays the mean
of whatever is currently in view on each chart.
"""
from __future__ import annotations

import customtkinter as ctk

from core.settings_store import format_timebase
from ui.base_view import BaseView
from ui.theme import (
    BG_CARD, TXT_PRIMARY, TXT_SECONDARY, BRAND_CYAN, SUCCESS_GREEN, WARNING_AMBER,
    FONT_H1, FONT_BODY, FONT_LABEL, RADIUS_LG,
)
from ui.view_registry import ViewRegistry
from ui.widgets.trend_chart import TrendChart

_FULL = "Full session"


class TrendsView(BaseView):
    TITLE = "Trends"

    def build_body(self):
        head = ctk.CTkFrame(self, fg_color="transparent")
        head.pack(fill="x", padx=24, pady=(18, 6))
        ctk.CTkLabel(head, text="Trends", font=FONT_H1,
                     text_color=TXT_PRIMARY).pack(side="left")
        self.source_lbl = ctk.CTkLabel(head, text="Live session", font=FONT_BODY,
                                       text_color=TXT_SECONDARY)
        self.source_lbl.pack(side="left", padx=12)
        ctk.CTkButton(head, text="Back to Live", width=110,
                      command=self._back_to_live).pack(side="right")

        # --- controls: window selector + average toggle ---------------
        ctrl = ctk.CTkFrame(self, fg_color="transparent")
        ctrl.pack(fill="x", padx=24, pady=(0, 6))
        ctk.CTkLabel(ctrl, text="Time base", font=FONT_LABEL,
                     text_color=TXT_SECONDARY).pack(side="left")
        self.win_var = ctk.StringVar(value=_FULL)
        self.win_box = ctk.CTkComboBox(ctrl, width=120, variable=self.win_var,
                                       command=lambda _=None: self._render())
        self.win_box.pack(side="left", padx=(8, 16))

        self.avg_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(ctrl, text="Show averages", variable=self.avg_var,
                        command=self._on_avg).pack(side="left")

        self.span_lbl = ctk.CTkLabel(ctrl, text="", font=FONT_BODY,
                                     text_color=TXT_SECONDARY)
        self.span_lbl.pack(side="right")

        card = ctk.CTkFrame(self, fg_color=BG_CARD, corner_radius=RADIUS_LG)
        card.pack(expand=True, fill="both", padx=24, pady=(0, 24))

        self.chart_rate = TrendChart(card, "Rate", "s/d", BRAND_CYAN, band=(-10, 10))
        self.chart_amp = TrendChart(card, "Amplitude", "°", SUCCESS_GREEN, band=(250, 320))
        self.chart_be = TrendChart(card, "Beat error", "ms", WARNING_AMBER, band=(0, 0.5))
        self.charts = (self.chart_rate, self.chart_amp, self.chart_be)
        for ch in self.charts:
            ch.pack(fill="both", expand=True, padx=12, pady=8)

        # When None we follow the live trail; otherwise show this fixed series.
        self._frozen: list[dict] | None = None
        self.refresh_timebases()

    # -- controls ------------------------------------------------------
    def refresh_timebases(self):
        secs = [int(s) for s in self.app.settings.get("avg_timebases", [30])]
        self._win_map = {format_timebase(s): s for s in secs}
        self.win_box.configure(values=[_FULL] + list(self._win_map))
        if self.win_var.get() not in self._win_map and self.win_var.get() != _FULL:
            self.win_var.set(_FULL)

    def _on_avg(self):
        on = self.avg_var.get()
        for ch in self.charts:
            ch.set_show_average(on)

    # -- external entry point from the History view -------------------
    def show_samples(self, samples, source: str) -> None:
        self._frozen = list(samples)
        self.source_lbl.configure(text=source)
        self.app.select_view("trends")
        self._render()

    def _back_to_live(self):
        self._frozen = None
        self.source_lbl.configure(text="Live session")
        self._render()

    # -- lifecycle -----------------------------------------------------
    def on_show(self):
        self._render()

    def on_metrics(self, m):
        if self._frozen is None:
            self._render()

    def _render(self):
        rows = self._frozen if self._frozen is not None else self.app.samples()
        if not rows:
            for ch in self.charts:
                ch.set_series([], [])
            self.span_lbl.configure(text="no samples")
            return

        # Trim to the selected window (relative to the newest sample).
        win = self._win_map.get(self.win_var.get())   # None for "Full session"
        if win is not None:
            cutoff = rows[-1]["t"] - win
            rows = [r for r in rows if r["t"] >= cutoff] or rows[-1:]

        t0 = rows[0]["t"]
        span = rows[-1]["t"] - t0
        ts = [r["t"] - t0 for r in rows]
        self.chart_rate.set_series(ts, [r["rate"] for r in rows])
        self.chart_amp.set_series(ts, [r["amp"] for r in rows])
        self.chart_be.set_series(ts, [r["be"] for r in rows])
        self.span_lbl.configure(
            text=f"{len(rows)} pts · {self._fmt_span(span)}")

    @staticmethod
    def _fmt_span(seconds: float) -> str:
        s = int(round(seconds))
        return f"{s // 60}:{s % 60:02d}" if s >= 60 else f"{s}s"


ViewRegistry.register("trends", "Trends", "TRN", TrendsView, order=20)
