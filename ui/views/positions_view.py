"""PositionsView — capture rate/amplitude/beat-error per position + deltas.

Two ways to capture each position (DU/DD/CU/CD/CL/CR):
  * Manual — press Capture to snapshot the current live reading.
  * Auto run — place the watch, start the run, and after a configurable settle
    time each position is captured automatically; you're then prompted to move
    to the next, and at the end to save or redo the whole run.

The footer shows the regulation spread and the run averages; Save writes the
session + its trend trail to the historian, and Export PDF produces a report.
"""
from __future__ import annotations

import math
import time
from tkinter import messagebox

import customtkinter as ctk

from core.criteria import Criteria, evaluate_session
from core.session import POSITIONS
from ui.base_view import BaseView
from ui.report_export import export_report_dialog
from ui.theme import (
    BG_CARD, BG_MAIN, BORDER_DARK, TXT_PRIMARY, TXT_SECONDARY, BRAND_CYAN,
    SUCCESS_GREEN, WARNING_AMBER, ERROR_RED, FONT_H1, FONT_H3, FONT_LABEL, FONT_BODY,
    RADIUS_LG, BORDER_W, BTN_NAVY, BTN_TEAL, BTN_RED,
)
from ui.view_registry import ViewRegistry

_DASH = "– – –"
_MONO = ("Consolas", 16, "bold")
_MONO_SM = ("Consolas", 13)
_POLL_MS = 200       # auto-run ticker cadence


class PositionsView(BaseView):
    TITLE = "Positions"

    def build_body(self):
        ctk.CTkLabel(self, text="Positional Measurement", font=FONT_H1,
                     text_color=TXT_PRIMARY).pack(anchor="w", padx=24, pady=(18, 6))

        self._auto = None          # auto-run state, or None when idle

        # --- header: watch name + actions -----------------------------
        head = ctk.CTkFrame(self, fg_color="transparent")
        head.pack(fill="x", padx=24, pady=(0, 8))
        ctk.CTkLabel(head, text="Watch", font=FONT_LABEL,
                     text_color=TXT_SECONDARY).pack(side="left", padx=(0, 6))
        self.watch_var = ctk.StringVar(value=self.app.session.watch_name)
        ctk.CTkEntry(head, textvariable=self.watch_var, width=220,
                     placeholder_text="e.g. Seiko 6309 #2").pack(side="left")
        ctk.CTkButton(head, text="Save Session", width=120, fg_color=BTN_TEAL,
                      command=self._save).pack(side="right")
        ctk.CTkButton(head, text="Export PDF", width=100, fg_color=BTN_NAVY,
                      command=self._export).pack(side="right", padx=(0, 8))
        ctk.CTkButton(head, text="New / Clear", width=110, fg_color=BTN_RED,
                      command=self._clear).pack(side="right", padx=(0, 8))

        # --- auto-run control bar -------------------------------------
        auto = ctk.CTkFrame(self, fg_color=BG_CARD, corner_radius=RADIUS_LG)
        auto.pack(fill="x", padx=24, pady=(0, 12))
        inner = ctk.CTkFrame(auto, fg_color="transparent")
        inner.pack(fill="x", padx=12, pady=10)
        ctk.CTkLabel(inner, text="Auto run", font=FONT_H3,
                     text_color=TXT_PRIMARY).pack(side="left")
        ctk.CTkLabel(inner, text="Settle (s)", font=FONT_LABEL,
                     text_color=TXT_SECONDARY).pack(side="left", padx=(16, 4))
        self.settle_var = ctk.StringVar(
            value=str(int(self.app.settings.get("stabilize_seconds", 15))))
        ctk.CTkEntry(inner, textvariable=self.settle_var, width=56).pack(side="left")
        self.start_btn = ctk.CTkButton(inner, text="Start ▶", width=90, fg_color=BTN_TEAL,
                                       command=self._auto_start)
        self.start_btn.pack(side="left", padx=(12, 0))
        self.continue_btn = ctk.CTkButton(inner, text="Continue", width=100,
                                          fg_color=BTN_NAVY, command=self._auto_continue)
        self.cancel_btn = ctk.CTkButton(inner, text="Stop", width=80, fg_color=BTN_RED,
                                        command=self._auto_cancel)
        self.auto_status = ctk.CTkLabel(auto, text="Idle — place the watch and Start, "
                                        "or capture positions manually.",
                                        font=FONT_BODY, text_color=TXT_SECONDARY)
        self.auto_status.pack(anchor="w", padx=14, pady=(0, 10))

        # --- capture grid ---------------------------------------------
        card = ctk.CTkFrame(self, fg_color=BG_CARD, corner_radius=RADIUS_LG)
        card.pack(fill="x", padx=24, pady=(0, 12))
        for c, w in ((0, 2), (1, 1), (2, 1), (3, 1), (4, 1), (5, 1)):
            card.grid_columnconfigure(c, weight=w)

        for c, txt in enumerate(("Position", "Rate s/d", "Amplitude °",
                                 "Beat error ms", "Captured", "")):
            ctk.CTkLabel(card, text=txt, font=FONT_LABEL,
                         text_color=TXT_SECONDARY).grid(
                row=0, column=c, sticky="w", padx=12, pady=(12, 4))

        self._rows: dict[str, dict] = {}
        self._capture_btns: dict[str, ctk.CTkButton] = {}
        for i, (code, name) in enumerate(POSITIONS, start=1):
            row_lbl = ctk.CTkLabel(card, text=f"{code} · {name}", font=FONT_H3,
                                   text_color=TXT_PRIMARY)
            row_lbl.grid(row=i, column=0, sticky="w", padx=12, pady=6)
            cells = {"label": row_lbl}
            for c, key in ((1, "rate"), (2, "amp"), (3, "be"), (4, "time")):
                lbl = ctk.CTkLabel(card, text=_DASH,
                                   font=_MONO if c < 4 else _MONO_SM,
                                   text_color=TXT_SECONDARY)
                lbl.grid(row=i, column=c, sticky="w", padx=12, pady=6)
                cells[key] = lbl
            btn = ctk.CTkButton(card, text="Capture", width=90, fg_color=BTN_NAVY,
                                command=lambda k=code: self._capture(k))
            btn.grid(row=i, column=5, sticky="e", padx=12, pady=6)
            self._capture_btns[code] = btn
            self._rows[code] = cells

        # --- delta + average footer -----------------------------------
        foot = ctk.CTkFrame(self, fg_color=BG_CARD, corner_radius=RADIUS_LG,
                            border_width=BORDER_W, border_color=BORDER_DARK)
        foot.pack(fill="x", padx=24, pady=(0, 16))
        self.delta_rate = self._stat(foot, "Rate spread (Δ s/d)", 0)
        self.delta_amp = self._stat(foot, "Amplitude spread (Δ °)", 1)
        self.avg_rate = self._stat(foot, "Avg rate (s/d)", 2)
        self.avg_amp = self._stat(foot, "Avg amplitude (°)", 3)
        self.avg_be = self._stat(foot, "Avg beat error (ms)", 4)
        self.delta_n = self._stat(foot, "Captured", 5)
        self.result_stat = self._stat(foot, "Result", 6)

        # --- live hint ------------------------------------------------
        self.hint = ctk.CTkLabel(self, text="", font=FONT_BODY,
                                 text_color=TXT_SECONDARY)
        self.hint.pack(anchor="w", padx=24)

        self._refresh()

    def _stat(self, parent, label, col):
        parent.grid_columnconfigure(col, weight=1)
        box = ctk.CTkFrame(parent, fg_color="transparent")
        box.grid(row=0, column=col, sticky="ew", padx=12, pady=12)
        ctk.CTkLabel(box, text=label, font=FONT_LABEL,
                     text_color=TXT_SECONDARY).pack(anchor="w")
        val = ctk.CTkLabel(box, text=_DASH, font=("Consolas", 20, "bold"),
                           text_color=BRAND_CYAN)
        val.pack(anchor="w")
        return val

    # -- lifecycle -----------------------------------------------------
    def on_show(self):
        self.watch_var.set(self.app.session.watch_name)
        self._refresh()

    def on_metrics(self, m):
        if self._auto is not None:
            return    # the auto-run owns the status line while active
        if m is None or not m.valid:
            self.hint.configure(text="Acquiring a stable reading…")
            return
        amp = "n/a" if math.isnan(m.amplitude_deg) else f"{m.amplitude_deg:.0f}°"
        self.hint.configure(
            text=f"Live: {m.rate_s_per_day:+.1f} s/d · {amp} · "
                 f"{m.beat_error_ms:.1f} ms — press Capture for a position.")

    # -- manual actions ------------------------------------------------
    def _capture(self, code):
        m = self.app.last_metrics
        if m is None or not m.valid:
            messagebox.showwarning("No reading",
                                   "Connect and wait for a stable reading first.",
                                   parent=self)
            return
        self.app.session.watch_name = self.watch_var.get().strip()
        self.app.session.record(code, m)
        self._refresh()

    def _clear(self):
        if self._auto is not None:
            self._auto_cancel()
        self.app.session.watch_name = self.watch_var.get().strip()
        self.app.settings.set("watch_name", self.app.session.watch_name)
        self.app.settings.save()
        self.app.new_session()
        self.watch_var.set(self.app.session.watch_name)
        self._refresh()

    def _save(self):
        sess = self.app.session
        sess.watch_name = self.watch_var.get().strip()
        if not sess.results:
            messagebox.showinfo("Nothing to save",
                                "Capture at least one position first.", parent=self)
            return False
        self.app.settings.set("watch_name", sess.watch_name)
        self.app.settings.save()
        try:
            if self.app.historian.engine is None:
                self.app.historian.connect()
            sid = self.app.historian.save_session(sess, self.app.samples())
        except Exception as exc:   # surface DB/driver issues plainly
            messagebox.showerror("Save failed", str(exc), parent=self)
            return False
        messagebox.showinfo("Session saved",
                            f"Saved “{sess.watch_name or 'watch'}” "
                            f"({len(sess.results)} positions) as #{sid}.", parent=self)
        hv = self.app.views.get("history")
        if hv is not None:
            hv.on_show()
        return True

    def _export(self):
        sess = self.app.session
        sess.watch_name = self.watch_var.get().strip()
        results = {c: vars(r) for c, r in sess.results.items()}
        export_report_dialog(
            self, watch_name=sess.watch_name, movement_label=sess.movement_label,
            bph=sess.bph, lift_angle=sess.lift_angle,
            started_at=sess.started_at, results=results, notes=sess.notes,
            criteria=Criteria.from_settings(self.app.settings))

    # -- auto run ------------------------------------------------------
    def _settle_seconds(self) -> int:
        try:
            s = int(float(self.settle_var.get()))
        except ValueError:
            s = 15
        return max(1, s)

    def _auto_start(self):
        if self.app.link is None:
            messagebox.showwarning("Not connected",
                                   "Connect a device before starting an auto run.",
                                   parent=self)
            return
        if self.app.session.results and not messagebox.askyesno(
                "Start auto run", "This clears the current captures and starts a "
                "fresh 6-position run. Continue?", parent=self):
            return
        settle = self._settle_seconds()
        self.app.settings.set("stabilize_seconds", settle)
        self.app.session.watch_name = self.watch_var.get().strip()
        self.app.new_session()
        self.watch_var.set(self.app.session.watch_name)
        self._auto = {"index": 0, "phase": "stabilising",
                      "deadline": time.monotonic() + settle, "settle": settle}
        self._auto_set_controls()
        self._refresh()
        self.after(_POLL_MS, self._auto_tick)

    def _auto_continue(self):
        if self._auto and self._auto["phase"] == "await_move":
            self._auto["phase"] = "stabilising"
            self._auto["deadline"] = time.monotonic() + self._auto["settle"]
            self._auto_set_controls()
            self.after(_POLL_MS, self._auto_tick)

    def _auto_cancel(self):
        self._auto = None
        self._auto_set_controls()
        self.auto_status.configure(
            text="Auto run stopped.", text_color=TXT_SECONDARY)

    def _auto_set_controls(self):
        """Show/hide the run buttons for the current phase."""
        phase = self._auto["phase"] if self._auto else None
        # Start is available only when idle.
        if phase is None:
            self.continue_btn.pack_forget()
            self.cancel_btn.pack_forget()
            self.start_btn.configure(state="normal")
            return
        self.start_btn.configure(state="disabled")
        if not self.cancel_btn.winfo_ismapped():
            self.cancel_btn.pack(side="left", padx=(8, 0))
        if phase == "await_move":
            if not self.continue_btn.winfo_ismapped():
                self.continue_btn.pack(side="left", padx=(8, 0))
        else:
            self.continue_btn.pack_forget()

    def _auto_tick(self):
        if self._auto is None:
            return
        phase = self._auto["phase"]
        code, name = POSITIONS[self._auto["index"]]

        if phase == "stabilising":
            remaining = self._auto["deadline"] - time.monotonic()
            m = self.app.last_metrics
            if remaining > 0:
                live = ""
                if m is not None and m.valid:
                    live = f"  ·  live {m.rate_s_per_day:+.1f} s/d"
                self.auto_status.configure(
                    text=f"Stabilising {code} · {name} — {math.ceil(remaining)} s{live}",
                    text_color=WARNING_AMBER)
            elif m is None or not m.valid:
                self.auto_status.configure(
                    text=f"{code} · {name}: waiting for a stable reading…",
                    text_color=WARNING_AMBER)
            else:
                self._auto_capture(code, name, m)
                return
            self.after(_POLL_MS, self._auto_tick)

        elif phase == "await_move":
            self.auto_status.configure(
                text=f"Captured. Move the watch to {code} · {name}, then press Continue.",
                text_color=BRAND_CYAN)
            # idle until Continue re-arms the ticker

    def _auto_capture(self, code, name, m):
        self.app.session.watch_name = self.watch_var.get().strip()
        self.app.session.record(code, m)
        self._refresh()
        if self._auto["index"] + 1 < len(POSITIONS):
            self._auto["index"] += 1
            self._auto["phase"] = "await_move"
            self._auto_set_controls()
            self._auto_tick()          # paint the move prompt immediately
        else:
            self._auto_finish()

    def _auto_finish(self):
        self._auto = None
        self._auto_set_controls()
        self.auto_status.configure(text="Run complete — all 6 positions captured.",
                                   text_color=SUCCESS_GREEN)
        choice = messagebox.askyesnocancel(
            "Run complete",
            "All positions captured.\n\nYes — save this record\n"
            "No — redo the run\nCancel — keep it on screen", parent=self)
        if choice is True:
            self._save()
        elif choice is False:
            self._auto_start()

    # -- render --------------------------------------------------------
    @staticmethod
    def _check_color(passed):
        if passed is None:
            return TXT_PRIMARY
        return SUCCESS_GREEN if passed else ERROR_RED

    def _refresh(self):
        sess = self.app.session
        criteria = Criteria.from_settings(self.app.settings)
        ev = evaluate_session(sess.results, criteria)
        target = None
        if self._auto and self._auto["phase"] in ("stabilising", "await_move"):
            target = POSITIONS[self._auto["index"]][0]
        for code, cells in self._rows.items():
            highlight = (code == target)
            cells["label"].configure(
                text_color=BRAND_CYAN if highlight else TXT_PRIMARY)
            r = sess.results.get(code)
            if r is None:
                for key in ("rate", "amp", "be", "time"):
                    cells[key].configure(text=_DASH, text_color=TXT_SECONDARY)
                continue
            chk = ev["per"].get(code, {}).get("checks", {})
            cells["rate"].configure(text=f"{r.rate_s_per_day:+.1f}",
                                    text_color=self._check_color(chk.get("rate")))
            amp = _DASH if math.isnan(r.amplitude_deg) else f"{r.amplitude_deg:.0f}"
            cells["amp"].configure(text=amp,
                                   text_color=self._check_color(chk.get("amplitude")))
            be = _DASH if math.isnan(r.beat_error_ms) else f"{r.beat_error_ms:.1f}"
            cells["be"].configure(text=be,
                                  text_color=self._check_color(chk.get("beat_error")))
            cells["time"].configure(text=time.strftime("%H:%M:%S",
                                    time.localtime(r.captured_at)), text_color=TXT_SECONDARY)

        dr = sess.rate_delta()
        da = sess.amplitude_delta()
        avg = sess.averages()
        self.delta_rate.configure(text=_DASH if dr is None else f"{dr:.1f}",
                                  text_color=self._check_color(ev["spread_pass"])
                                  if dr is not None else BRAND_CYAN)
        self.delta_amp.configure(text=_DASH if da is None else f"{da:.0f}")
        self.avg_rate.configure(
            text=_DASH if avg["rate_s_per_day"] is None else f"{avg['rate_s_per_day']:+.1f}")
        self.avg_amp.configure(
            text=_DASH if avg["amplitude_deg"] is None else f"{avg['amplitude_deg']:.0f}")
        self.avg_be.configure(
            text=_DASH if avg["beat_error_ms"] is None else f"{avg['beat_error_ms']:.2f}")
        self.delta_n.configure(text=f"{len(sess.results)} / {len(POSITIONS)}")

        ov = ev["overall"]
        self.result_stat.configure(
            text="—" if ov is None else ("PASS" if ov else "FAIL"),
            text_color=self._check_color(ov))


ViewRegistry.register("positions", "Positions", "POS", PositionsView, order=40)
