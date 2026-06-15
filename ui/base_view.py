"""BaseView — shared lifecycle and header for every registered view."""
from __future__ import annotations

import customtkinter as ctk

from ui.theme import BG_MAIN, BG_CARD, TXT_PRIMARY, FONT_H1, FONT_BODY, RADIUS_LG


class BaseView(ctk.CTkFrame):
    """Subclass and override TITLE plus build_body(). Optionally on_metrics()."""

    TITLE = "View"

    def __init__(self, parent, app):
        super().__init__(parent, fg_color=BG_MAIN, corner_radius=0)
        self.app = app
        self.build_body()

    def build_body(self) -> None:
        """Override to populate the view."""
        ctk.CTkLabel(self, text=self.TITLE, font=FONT_H1,
                     text_color=TXT_PRIMARY).pack(pady=20)

    # -- optional hooks the main window calls -------------------------
    def on_metrics(self, metrics) -> None:
        """Called each UI tick with the latest Metrics. Override if needed."""

    def on_show(self) -> None:
        """Called when this view is raised. Override if needed."""

    # -- helper for placeholder views ---------------------------------
    def _placeholder(self, message: str) -> None:
        card = ctk.CTkFrame(self, fg_color=BG_CARD, corner_radius=RADIUS_LG)
        card.pack(expand=True, fill="both", padx=24, pady=24)
        ctk.CTkLabel(card, text=self.TITLE, font=FONT_H1,
                     text_color=TXT_PRIMARY).pack(pady=(40, 8))
        ctk.CTkLabel(card, text=message, font=FONT_BODY,
                     text_color="gray60").pack()
