"""ConnectionBar — link selector + connect/disconnect + status indicator.

Mirrors the connection panels in the sibling apps: a transport dropdown (from
the link registry), an address field (serial port / IP), a connect toggle, and a
coloured status dot.
"""
from __future__ import annotations

import customtkinter as ctk

from links.link_manager import (
    registered_link_types, needs_address, list_serial_ports,
)
from ui.theme import (
    BG_CARD, BG_MAIN, BORDER_DARK, TXT_PRIMARY, TXT_SECONDARY, BRAND_CYAN,
    SUCCESS_GREEN, WARNING_AMBER, ERROR_RED, BTN_NAVY, BTN_RED, FONT_LABEL, FONT_BODY,
    RADIUS_LG, RADIUS_SM, BORDER_W, BTN_H,
)


class ConnectionBar(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent, fg_color=BG_CARD, corner_radius=RADIUS_LG,
                         border_width=BORDER_W, border_color=BORDER_DARK)
        self.app = app

        ctk.CTkLabel(self, text="Device", font=FONT_LABEL,
                     text_color=TXT_SECONDARY).pack(side="left", padx=(14, 6))

        self.kind_var = ctk.StringVar(value=app.settings.get("link_kind"))
        self.kind_box = ctk.CTkComboBox(self, width=150, variable=self.kind_var,
                                        values=registered_link_types(),
                                        command=lambda _=None: self._sync_address())
        self.kind_box.pack(side="left", padx=6)

        self.addr_var = ctk.StringVar(value=app.settings.get("link_address"))
        self.addr_box = ctk.CTkComboBox(self, width=170, variable=self.addr_var,
                                        values=list_serial_ports() or [""])
        self.addr_box.pack(side="left", padx=6)

        self.connect_btn = ctk.CTkButton(self, text="Connect", width=110, height=BTN_H,
                                         fg_color=BTN_NAVY, command=self._toggle)
        self.connect_btn.pack(side="left", padx=10)

        self.status_dot = ctk.CTkLabel(self, text="●", text_color=ERROR_RED,
                                       font=("Helvetica", 16))
        self.status_dot.pack(side="left")
        self.status_lbl = ctk.CTkLabel(self, text="Disconnected", font=FONT_BODY,
                                       text_color=TXT_SECONDARY)
        self.status_lbl.pack(side="left", padx=(2, 10))

        # Device health from the firmware STATUS frame (clock lock / rate / temp).
        self.health_lbl = ctk.CTkLabel(self, text="", font=FONT_BODY,
                                       text_color=TXT_SECONDARY)
        self.health_lbl.pack(side="left", padx=(0, 14))

        # --- right: the movement selected for this session ------------
        self.movement_chip = ctk.CTkFrame(self, fg_color=BG_MAIN,
                                          corner_radius=RADIUS_SM)
        self.movement_chip.pack(side="right", padx=(6, 14), pady=6)
        ctk.CTkLabel(self.movement_chip, text="MOVEMENT", font=("Helvetica", 9, "bold"),
                     text_color=TXT_SECONDARY).pack(side="left", padx=(10, 6))
        self.movement_lbl = ctk.CTkLabel(self.movement_chip, text="None selected",
                                         font=FONT_LABEL, text_color=TXT_SECONDARY)
        self.movement_lbl.pack(side="left", padx=(0, 12))

        self._sync_address()

    def set_movement(self, label: str | None) -> None:
        self.movement_lbl.configure(
            text=label or "None selected",
            text_color=BRAND_CYAN if label else TXT_SECONDARY)

    def _sync_address(self) -> None:
        kind = self.kind_var.get()
        if kind == "Serial (USB)":
            self.addr_box.configure(values=list_serial_ports() or [""], state="normal")
        elif needs_address(kind):
            self.addr_box.configure(state="normal")
        else:
            self.addr_box.configure(state="disabled")

    def _toggle(self) -> None:
        if self.app.link and self.app.link.is_open:
            self.app.disconnect()
        else:
            self.app.connect(self.kind_var.get(), self.addr_var.get())

    def set_connected(self, connected: bool, text: str = "") -> None:
        self.connect_btn.configure(text="Disconnect" if connected else "Connect",
                                   fg_color=BTN_RED if connected else BTN_NAVY)
        self.status_dot.configure(text_color=SUCCESS_GREEN if connected else ERROR_RED)
        self.status_lbl.configure(text=text or ("Connected" if connected else "Disconnected"),
                                  text_color=TXT_PRIMARY if connected else TXT_SECONDARY)
        if not connected:
            self.health_lbl.configure(text="")

    def set_device_status(self, st) -> None:
        """Reflect a firmware STATUS frame (clock lock / sample rate / temp)."""
        if st is None:
            self.health_lbl.configure(text="")
            return
        lock = "CLK ✓ locked" if st.clock_locked else "CLK ✗ no 32kHz"
        self.health_lbl.configure(
            text=f"{lock}  ·  {st.sample_rate} Hz  ·  {st.temperature_c:.1f} °C",
            text_color=SUCCESS_GREEN if st.clock_locked else WARNING_AMBER)
