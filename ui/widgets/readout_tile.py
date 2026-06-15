"""ReadoutTile — a big metric card (value + units + label)."""
from __future__ import annotations

import customtkinter as ctk

from ui.theme import (
    BG_CARD, BORDER_DARK, TXT_PRIMARY, TXT_SECONDARY, BRAND_CYAN,
    RADIUS_LG, BORDER_W,
)

_VALUE_FONT = ("Consolas", 46, "bold")
_UNIT_FONT = ("Consolas", 16)
_LABEL_FONT = ("Helvetica", 12, "bold")
_AVG_FONT = ("Consolas", 14)


class ReadoutTile(ctk.CTkFrame):
    def __init__(self, parent, label: str, units: str, accent: str = BRAND_CYAN):
        super().__init__(parent, fg_color=BG_CARD, corner_radius=RADIUS_LG,
                         border_width=BORDER_W, border_color=BORDER_DARK)
        self.accent = accent
        self.units = units
        self.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(self, text=label.upper(), font=_LABEL_FONT,
                     text_color=TXT_SECONDARY).grid(row=0, column=0, pady=(12, 0))

        row = ctk.CTkFrame(self, fg_color="transparent")
        row.grid(row=1, column=0, pady=(2, 0))
        self._value = ctk.CTkLabel(row, text="– – –", font=_VALUE_FONT,
                                   text_color=accent)
        self._value.pack(side="left")
        ctk.CTkLabel(row, text=" " + units, font=_UNIT_FONT,
                     text_color=TXT_SECONDARY).pack(side="left", anchor="s", pady=(0, 10))

        # Secondary line: rolling average over the selected time base.
        self._avg = ctk.CTkLabel(self, text="avg  – – –", font=_AVG_FONT,
                                 text_color=TXT_SECONDARY)
        self._avg.grid(row=2, column=0, pady=(0, 12))

    def set_value(self, text: str, color: str | None = None) -> None:
        self._value.configure(text=text, text_color=color or self.accent)

    def set_average(self, text: str) -> None:
        self._avg.configure(text=text)
