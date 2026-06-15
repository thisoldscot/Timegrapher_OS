"""LiveView — the main instrument: four big readouts + the paper-tape trace.

Each readout shows the instantaneous value and, beneath it, a rolling average
over a user-selectable time base (10 s … 5 min) so a noisy live figure can be
read as a steady mean.
"""
from __future__ import annotations

import math
import statistics
import time
from collections import deque

import customtkinter as ctk

from ui.base_view import BaseView
from ui.theme import (
    BG_MAIN, BG_CARD, BORDER_DARK, TXT_PRIMARY, TXT_SECONDARY,
    BRAND_CYAN, SUCCESS_GREEN, WARNING_AMBER, ERROR_RED, CAUTION_ORANGE,
    RADIUS_LG, BORDER_W, FONT_H3, FONT_LABEL,
)
from core.settings_store import format_timebase
from ui.view_registry import ViewRegistry
from ui.widgets.readout_tile import ReadoutTile
from .paper_tape import PaperTape


class LiveView(BaseView):
    TITLE = "Live"

    def build_body(self) -> None:
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # rolling history of (monotonic_t, rate, amp, be, bph) for the averages
        self._hist: deque = deque(maxlen=8000)
        self._tb_seconds = int(self.app.settings.get("avg_default", 30))

        # --- left: time-base control + stacked readouts ---------------
        left = ctk.CTkFrame(self, fg_color=BG_MAIN, corner_radius=0, width=320)
        left.grid(row=0, column=0, sticky="ns", padx=(12, 6), pady=12)
        left.grid_propagate(False)
        left.grid_columnconfigure(0, weight=1)

        ctrl = ctk.CTkFrame(left, fg_color="transparent")
        ctrl.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        ctk.CTkLabel(ctrl, text="Average over", font=FONT_LABEL,
                     text_color=TXT_SECONDARY).pack(side="left")
        self.tb_var = ctk.StringVar(value=format_timebase(self._tb_seconds))
        self.tb_box = ctk.CTkComboBox(ctrl, width=110, variable=self.tb_var,
                                      command=self._on_timebase)
        self.tb_box.pack(side="right")
        self.refresh_timebases()

        self.tile_rate = ReadoutTile(left, "Rate", "s/d", BRAND_CYAN)
        self.tile_amp = ReadoutTile(left, "Amplitude", "°", SUCCESS_GREEN)
        self.tile_be = ReadoutTile(left, "Beat Error", "ms", WARNING_AMBER)
        self.tile_bph = ReadoutTile(left, "Beat Rate", "bph", TXT_PRIMARY)
        for i, tile in enumerate((self.tile_rate, self.tile_amp, self.tile_be, self.tile_bph),
                                 start=1):
            tile.grid(row=i, column=0, sticky="ew", pady=(0, 8))
            left.grid_rowconfigure(i, weight=1)

        # --- right: paper tape ----------------------------------------
        right = ctk.CTkFrame(self, fg_color=BG_CARD, corner_radius=RADIUS_LG,
                             border_width=BORDER_W, border_color=BORDER_DARK)
        right.grid(row=0, column=1, sticky="nsew", padx=(6, 12), pady=12)
        right.grid_rowconfigure(1, weight=1)
        right.grid_columnconfigure(0, weight=1)

        header = ctk.CTkFrame(right, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=12, pady=(10, 4))
        ctk.CTkLabel(header, text="Trace", font=FONT_H3,
                     text_color=TXT_PRIMARY).pack(side="left")
        self.status_lbl = ctk.CTkLabel(header, text="Waiting for beats…",
                                       font=("Consolas", 11), text_color=TXT_SECONDARY)
        self.status_lbl.pack(side="right")

        self.tape = PaperTape(right)
        self.tape.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))

    # -- fed by main_window ------------------------------------------
    def push_beat(self, onset_s: float, bph: float) -> None:
        self.tape.push_beat(onset_s, bph)

    def reset(self) -> None:
        self.tape.reset()
        self._hist.clear()

    def refresh_timebases(self) -> None:
        """Rebuild the time-base menu from the (editable) settings list."""
        secs = [int(s) for s in self.app.settings.get("avg_timebases", [30])]
        self._tb_map = {format_timebase(s): s for s in secs}
        self.tb_box.configure(values=list(self._tb_map))
        # Keep the current pick if still valid, else fall back to the default.
        if self.tb_var.get() not in self._tb_map:
            default = int(self.app.settings.get("avg_default", secs[0] if secs else 30))
            self.tb_var.set(format_timebase(default))
        self._tb_seconds = self._tb_map.get(self.tb_var.get(),
                                            next(iter(self._tb_map.values()), 30))

    def _on_timebase(self, _=None) -> None:
        self._tb_seconds = self._tb_map.get(self.tb_var.get(), self._tb_seconds)

    # -- averaging ----------------------------------------------------
    def _record(self, m) -> None:
        self._hist.append((time.monotonic(), m.rate_s_per_day,
                           m.amplitude_deg, m.beat_error_ms, m.bph))

    def _window(self):
        cutoff = time.monotonic() - self._tb_seconds
        return [row for row in self._hist if row[0] >= cutoff]

    @staticmethod
    def _avg(values):
        clean = [v for v in values if v is not None and not math.isnan(v)]
        return statistics.fmean(clean) if clean else None

    def _update_averages(self) -> None:
        rows = self._window()
        rate = self._avg([r[1] for r in rows])
        amp = self._avg([r[2] for r in rows])
        be = self._avg([r[3] for r in rows])
        bph = self._avg([r[4] for r in rows])
        n = len(rows)
        self.tile_rate.set_average(f"avg  {rate:+.1f} s/d" if rate is not None else "avg  – – –")
        self.tile_amp.set_average(f"avg  {amp:.0f}°" if amp is not None else "avg  – – –")
        self.tile_be.set_average(f"avg  {be:.2f} ms" if be is not None else "avg  – – –")
        self.tile_bph.set_average(f"n={n}" if bph is None else f"avg  {bph:.0f}")

    def on_metrics(self, m) -> None:
        self.tape.redraw()
        if not m.valid:
            for t in (self.tile_rate, self.tile_amp, self.tile_be, self.tile_bph):
                t.set_value("– – –", TXT_SECONDARY)
            self.status_lbl.configure(text=f"Acquiring… ({m.beats_in_window} beats)")
            return

        self._record(m)

        rate_color = SUCCESS_GREEN if abs(m.rate_s_per_day) <= 10 else (
            WARNING_AMBER if abs(m.rate_s_per_day) <= 30 else ERROR_RED)
        self.tile_rate.set_value(f"{m.rate_s_per_day:+.1f}", rate_color)

        if math.isnan(m.amplitude_deg):
            self.tile_amp.set_value("– – –", TXT_SECONDARY)
        else:
            amp_color = SUCCESS_GREEN if 250 <= m.amplitude_deg <= 320 else CAUTION_ORANGE
            self.tile_amp.set_value(f"{m.amplitude_deg:.0f}", amp_color)

        be_color = SUCCESS_GREEN if m.beat_error_ms <= 0.5 else (
            WARNING_AMBER if m.beat_error_ms <= 1.0 else ERROR_RED)
        self.tile_be.set_value(f"{m.beat_error_ms:.1f}" if not math.isnan(m.beat_error_ms)
                               else "– – –", be_color)

        self.tile_bph.set_value(f"{m.bph:.0f}", TXT_PRIMARY)
        self._update_averages()

        lock = "lock" if m.bph_locked else f"~{m.raw_bph:.0f}"
        self.status_lbl.configure(
            text=f"{m.beats_in_window} beats · conf {m.confidence*100:.0f}% · {lock}")


ViewRegistry.register("live", "Live", "LIV", LiveView, order=10)
