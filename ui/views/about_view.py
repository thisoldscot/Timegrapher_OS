"""AboutView — app info plus editable repository / website / social links.

All URLs live in the LINKS dict below so they can be updated in one place at a
later date. Leave a value as an empty string to grey-out (disable) that link.
"""
from __future__ import annotations

import webbrowser

import customtkinter as ctk

from ui.base_view import BaseView
from ui.theme import (
    BG_CARD, TXT_PRIMARY, TXT_SECONDARY, TXT_ACCENT, BRAND_CYAN,
    FONT_H1, FONT_H2, FONT_H3, FONT_BODY, RADIUS_LG, BTN_NAVY, BTN_TEAL,
)
from ui.view_registry import ViewRegistry

# --- editable link targets ----------------------------------------------
# Update these as the project's public presence comes online. An empty string
# disables (greys out) that link.
LINKS = {
    "github": "https://github.com/your-org/timegrapher-studio",
    "website": "https://example.com",
    "youtube": "https://youtube.com/@yourchannel",
    "tiktok": "https://www.tiktok.com/@yourhandle",
    "instagram": "https://www.instagram.com/yourhandle",
}

_TAGLINE = ("System Integrator Apps — wristwatch diagnostics\n"
            "ESP32 · PCM1808 · DS3231 (±2 ppm reference)")


class AboutView(BaseView):
    TITLE = "About"

    def build_body(self):
        ctk.CTkLabel(self, text="Timegrapher Studio", font=FONT_H1,
                     text_color=TXT_PRIMARY).pack(anchor="w", padx=24, pady=(18, 2))
        ctk.CTkLabel(self, text=_TAGLINE, font=FONT_BODY, justify="left",
                     text_color=TXT_SECONDARY).pack(anchor="w", padx=24, pady=(0, 16))

        # --- repository -----------------------------------------------
        self._link_card("Repository",
                        "Source code, issues and releases on GitHub.",
                        "github", "Open GitHub")

        # --- website --------------------------------------------------
        self._link_card("Website",
                        "Product page, documentation and support.",
                        "website", "Open Website")

        # --- social row -----------------------------------------------
        social = ctk.CTkFrame(self, fg_color=BG_CARD, corner_radius=RADIUS_LG)
        social.pack(fill="x", padx=24, pady=(8, 16))
        ctk.CTkLabel(social, text="Follow", font=FONT_H3,
                     text_color=TXT_PRIMARY).pack(side="left", padx=(16, 8), pady=14)
        for key, text in (("youtube", "YouTube"), ("tiktok", "TikTok"),
                          ("instagram", "Instagram")):
            self._social_button(social, key, text)

    # -- builders ------------------------------------------------------
    def _link_card(self, title, desc, key, button_text):
        card = ctk.CTkFrame(self, fg_color=BG_CARD, corner_radius=RADIUS_LG)
        card.pack(fill="x", padx=24, pady=(0, 12))
        card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(card, text=title, font=FONT_H2,
                     text_color=TXT_PRIMARY).grid(row=0, column=0, sticky="w",
                                                  padx=16, pady=(12, 0))
        ctk.CTkLabel(card, text=desc, font=FONT_BODY,
                     text_color=TXT_SECONDARY).grid(row=1, column=0, sticky="w",
                                                    padx=16, pady=(0, 2))
        url = LINKS.get(key, "")
        ctk.CTkLabel(card, text=url or "(not set)", font=("Consolas", 11),
                     text_color=TXT_ACCENT if url else TXT_SECONDARY).grid(
            row=2, column=0, sticky="w", padx=16, pady=(0, 12))

        btn = ctk.CTkButton(card, text=button_text, width=130, fg_color=BTN_TEAL,
                            command=lambda k=key: self._open(k))
        btn.grid(row=0, column=1, rowspan=3, sticky="e", padx=16, pady=12)
        if not url:
            btn.configure(state="disabled")

    def _social_button(self, parent, key, text):
        btn = ctk.CTkButton(parent, text=text, width=110, fg_color=BTN_NAVY,
                            command=lambda k=key: self._open(k))
        btn.pack(side="left", padx=(0, 8), pady=14)
        if not LINKS.get(key):
            btn.configure(state="disabled")

    # -- actions -------------------------------------------------------
    @staticmethod
    def _open(key):
        url = LINKS.get(key, "")
        if url:
            webbrowser.open(url)


ViewRegistry.register("about", "About", "ABT", AboutView, order=90)
