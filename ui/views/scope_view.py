"""ScopeView — beat-waveform oscilloscope from the decimated WAVE stream.

While this view is on screen the host subscribes to the envelope stream (CMD
{"waveform":true}); the main window drains the chunks each tick and feeds them
here. Each beat overlays trigger-aligned on the scope, so you can see the
escapement's acoustic signature and confirm clean beat detection. The header
mirrors the live amplitude / beat rate so the trace can be read in context.
"""
from __future__ import annotations

import math

import customtkinter as ctk

from ui.base_view import BaseView
from ui.theme import (
    BG_CARD, BORDER_DARK, TXT_PRIMARY, TXT_SECONDARY, BRAND_CYAN, SUCCESS_GREEN,
    FONT_H1, FONT_H3, FONT_BODY, RADIUS_LG, BORDER_W,
)
from ui.view_registry import ViewRegistry
from ui.widgets.scope_canvas import ScopeCanvas


class ScopeView(BaseView):
    TITLE = "Scope"

    def build_body(self):
        head = ctk.CTkFrame(self, fg_color="transparent")
        head.pack(fill="x", padx=24, pady=(18, 6))
        ctk.CTkLabel(head, text="Scope", font=FONT_H1,
                     text_color=TXT_PRIMARY).pack(side="left")
        ctk.CTkLabel(head, text="Beat envelope · trigger-aligned", font=FONT_BODY,
                     text_color=TXT_SECONDARY).pack(side="left", padx=12)
        self.readout_lbl = ctk.CTkLabel(head, text="—", font=("Consolas", 13),
                                        text_color=BRAND_CYAN)
        self.readout_lbl.pack(side="right")

        card = ctk.CTkFrame(self, fg_color=BG_CARD, corner_radius=RADIUS_LG,
                            border_width=BORDER_W, border_color=BORDER_DARK)
        card.pack(expand=True, fill="both", padx=24, pady=(0, 24))
        card.grid_rowconfigure(1, weight=1)
        card.grid_columnconfigure(0, weight=1)

        sub = ctk.CTkFrame(card, fg_color="transparent")
        sub.grid(row=0, column=0, sticky="ew", padx=12, pady=(10, 4))
        ctk.CTkLabel(sub, text="Trace", font=FONT_H3,
                     text_color=TXT_PRIMARY).pack(side="left")
        self.status_lbl = ctk.CTkLabel(sub, text="Not connected",
                                       font=("Consolas", 11), text_color=TXT_SECONDARY)
        self.status_lbl.pack(side="right")

        self.scope = ScopeCanvas(card)
        self.scope.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))
        self._count = 0

    # -- fed by main_window ------------------------------------------
    def push_wave(self, wf) -> None:
        self.scope.push(wf.samples, wf.sample_rate)
        self._count += 1
        self.status_lbl.configure(text=f"{self._count} sweeps")

    def reset(self) -> None:
        self.scope.reset()
        self._count = 0
        self.status_lbl.configure(text="Not connected")

    def on_show(self):
        if self.app.link is None:
            self.status_lbl.configure(text="Connect a device to see the trace")

    def on_metrics(self, m):
        if m is None or not m.valid:
            self.readout_lbl.configure(text="—")
            return
        amp = "– – –" if math.isnan(m.amplitude_deg) else f"{m.amplitude_deg:.0f}°"
        color = SUCCESS_GREEN if not math.isnan(m.amplitude_deg) else TXT_SECONDARY
        self.readout_lbl.configure(text=f"amp {amp}  ·  {m.bph:.0f} bph",
                                   text_color=color)


ViewRegistry.register("scope", "Scope", "SCP", ScopeView, order=30)
