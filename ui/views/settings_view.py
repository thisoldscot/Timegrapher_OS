"""SettingsView — session movement, lift angle, BPH mode, analysis window.

Edits flow straight into the analyzer and the persisted settings store. Picking
a movement here is the same action as "Use for Session" on the Movements page:
it pins that movement's lift angle + BPH and shows it in the header.
"""
import customtkinter as ctk

from core.constants import STANDARD_BPH
from core.settings_store import format_timebase, parse_timebases
from ui.base_view import BaseView
from ui.theme import (
    BG_CARD, TXT_PRIMARY, TXT_SECONDARY, FONT_H1, FONT_H3, FONT_BODY,
    RADIUS_LG, BTN_NAVY, BTN_TEAL,
)
from ui.view_registry import ViewRegistry

_NONE = "(none)"


class SettingsView(BaseView):
    TITLE = "Settings"

    def build_body(self):
        ctk.CTkLabel(self, text="Settings", font=FONT_H1,
                     text_color=TXT_PRIMARY).pack(anchor="w", padx=24, pady=(18, 6))

        st = self.app.settings

        # --- session movement ----------------------------------------
        mcard = ctk.CTkFrame(self, fg_color=BG_CARD, corner_radius=RADIUS_LG)
        mcard.pack(fill="x", padx=24, pady=(0, 12))
        mcard.grid_columnconfigure(1, weight=1)
        self._row(mcard, 0, "Session movement",
                  "Pins this caliber's lift angle + BPH and shows it in the header.")
        self.movement_var = ctk.StringVar()
        self.movement_box = ctk.CTkComboBox(
            mcard, width=240, variable=self.movement_var,
            values=self._movement_values(),
            command=lambda _=None: self._on_movement())
        self.movement_box.grid(row=0, column=2, padx=16, pady=10)

        # --- analyzer parameters -------------------------------------
        card = ctk.CTkFrame(self, fg_color=BG_CARD, corner_radius=RADIUS_LG)
        card.pack(fill="x", padx=24, pady=(0, 16))
        card.grid_columnconfigure(1, weight=1)

        self._row(card, 0, "Lift angle (°)",
                  "Movement-specific; sets the amplitude scale.")
        self.lift_var = ctk.StringVar(value=str(st.get("lift_angle")))
        ctk.CTkEntry(card, textvariable=self.lift_var, width=120).grid(
            row=0, column=2, padx=16, pady=10)

        self._row(card, 1, "Beat rate (BPH)",
                  "Auto-detect, or pin to a known train rate.")
        self.bph_var = ctk.StringVar(value=str(st.get("bph_mode")))
        ctk.CTkComboBox(card, width=120, variable=self.bph_var,
                        values=["auto", *[str(b) for b in STANDARD_BPH]]).grid(
            row=1, column=2, padx=16, pady=10)

        self._row(card, 2, "Analysis window (s)",
                  "Sliding window length for the metric fits.")
        self.win_var = ctk.StringVar(value=str(st.get("window_seconds")))
        ctk.CTkEntry(card, textvariable=self.win_var, width=120).grid(
            row=2, column=2, padx=16, pady=10)

        # --- averaging time bases ------------------------------------
        acard = ctk.CTkFrame(self, fg_color=BG_CARD, corner_radius=RADIUS_LG)
        acard.pack(fill="x", padx=24, pady=(0, 16))
        acard.grid_columnconfigure(1, weight=1)

        self._row(acard, 0, "Average windows",
                  "Comma-separated, e.g. 10s, 30s, 1 min, 2 min, 5 min.")
        self.tb_var = ctk.StringVar()
        ctk.CTkEntry(acard, textvariable=self.tb_var, width=240).grid(
            row=0, column=2, padx=16, pady=10)

        self._row(acard, 1, "Default window",
                  "Window selected on the Live view at startup.")
        self.tb_default_var = ctk.StringVar()
        self.tb_default_box = ctk.CTkComboBox(acard, width=120,
                                              variable=self.tb_default_var)
        self.tb_default_box.grid(row=1, column=2, padx=16, pady=10)

        # --- pass / fail tolerances ----------------------------------
        tcard = ctk.CTkFrame(self, fg_color=BG_CARD, corner_radius=RADIUS_LG)
        tcard.pack(fill="x", padx=24, pady=(0, 16))
        ctk.CTkLabel(tcard, text="Pass / fail tolerances", font=FONT_H3,
                     text_color=TXT_PRIMARY).grid(row=0, column=0, columnspan=6,
                                                  sticky="w", padx=16, pady=(10, 2))
        ctk.CTkLabel(tcard, text="Used to judge each position and the whole run.",
                     font=FONT_BODY, text_color=TXT_SECONDARY).grid(
            row=1, column=0, columnspan=6, sticky="w", padx=16)
        self._tol_vars: dict[str, ctk.StringVar] = {}
        fields = [
            ("tol_rate_target", "Rate target (s/d)"),
            ("tol_rate", "Rate ± (s/d)"),
            ("tol_be_max", "Beat error max (ms)"),
            ("tol_amp_min", "Amplitude min (°)"),
            ("tol_amp_max", "Amplitude max (°)"),
            ("tol_spread", "Rate spread max (s/d)"),
        ]
        for i, (key, label) in enumerate(fields):
            self._tol_field(tcard, 2 + i // 3, i % 3, key, label)

        ctk.CTkButton(self, text="Apply", fg_color=BTN_TEAL, width=140,
                      command=self._apply).pack(anchor="w", padx=24)

        self.refresh_from_settings()

    def _tol_field(self, parent, r, c, key, label):
        box = ctk.CTkFrame(parent, fg_color="transparent")
        box.grid(row=r, column=c, sticky="w", padx=16, pady=(6, 10))
        ctk.CTkLabel(box, text=label, font=FONT_BODY,
                     text_color=TXT_SECONDARY).pack(anchor="w")
        var = ctk.StringVar()
        ctk.CTkEntry(box, textvariable=var, width=110).pack(anchor="w")
        self._tol_vars[key] = var

    def _movement_values(self):
        return [_NONE] + [m.label for m in self.app.movement_db.all()]

    def _row(self, parent, r, label, desc):
        ctk.CTkLabel(parent, text=label, font=FONT_H3,
                     text_color=TXT_PRIMARY).grid(row=r, column=0, sticky="w", padx=16, pady=(10, 0))
        ctk.CTkLabel(parent, text=desc, font=FONT_BODY,
                     text_color=TXT_SECONDARY).grid(row=r, column=1, sticky="w", padx=8)

    # -- sync the form with current settings/movement -----------------
    def on_show(self):
        self.movement_box.configure(values=self._movement_values())
        self.refresh_from_settings()

    def refresh_from_settings(self):
        st = self.app.settings
        cur = getattr(self.app.current_movement, "label", None)
        self.movement_var.set(cur or _NONE)
        self.lift_var.set(str(st.get("lift_angle")))
        self.bph_var.set(str(st.get("bph_mode")))
        self.win_var.set(str(st.get("window_seconds")))

        bases = [int(s) for s in st.get("avg_timebases", [])]
        self.tb_var.set(", ".join(format_timebase(s) for s in bases))
        labels = [format_timebase(s) for s in bases]
        self.tb_default_box.configure(values=labels)
        self.tb_default_var.set(format_timebase(int(st.get("avg_default", 30))))

        for key, var in self._tol_vars.items():
            var.set(str(st.get(key)))

    # -- actions ------------------------------------------------------
    def _on_movement(self):
        label = self.movement_var.get()
        if label == _NONE:
            self.app.select_movement(None)
        else:
            self.app.select_movement(self.app.movement_db.find(label))

    def _apply(self):
        try:
            lift = float(self.lift_var.get())
            win = float(self.win_var.get())
        except ValueError:
            return
        bph_mode = self.bph_var.get()
        bph_mode = int(bph_mode) if bph_mode.isdigit() else "auto"

        bases = parse_timebases(self.tb_var.get())
        if not bases:
            bases = [int(s) for s in self.app.settings.get("avg_timebases", [30])]
        # Default window must be one of the configured windows.
        default = parse_timebases(self.tb_default_var.get())
        default = default[0] if default and default[0] in bases else bases[0]

        st = self.app.settings
        st.set("lift_angle", lift)
        st.set("bph_mode", bph_mode)
        st.set("window_seconds", win)
        st.set("avg_timebases", bases)
        st.set("avg_default", default)
        # Pass/fail tolerances — keep the prior value on any unparseable field.
        for key, var in self._tol_vars.items():
            try:
                st.set(key, float(var.get()))
            except ValueError:
                pass
        st.save()
        self.app.apply_analyzer_settings()
        # Push the new windows to the views that use them.
        for key in ("live", "trends"):
            v = self.app.views.get(key)
            if v is not None and hasattr(v, "refresh_timebases"):
                v.refresh_timebases()
        pv = self.app.views.get("positions")
        if pv is not None:
            pv._refresh()
        self.refresh_from_settings()


ViewRegistry.register("settings", "Settings", "SET", SettingsView, order=80)
