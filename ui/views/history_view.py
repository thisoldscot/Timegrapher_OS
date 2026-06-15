"""HistoryView — saved sessions: browse, inspect positions, delete, open trends.

Reads the SQLite historian. Selecting a session shows its captured positions;
"Open in Trends" pushes that session's stored sample trail into the Trends view.
"""
from __future__ import annotations

import time
from tkinter import ttk, messagebox

import customtkinter as ctk

from core.criteria import Criteria, evaluate_session
from core.session import POSITIONS
from ui.base_view import BaseView
from ui.report_export import export_report_dialog
from ui.theme import (
    BG_CARD, BG_MAIN, BORDER_DARK, TXT_PRIMARY, TXT_SECONDARY, BRAND_CYAN,
    SUCCESS_GREEN, ERROR_RED, FONT_H1, FONT_H3, FONT_BODY, FONT_LABEL, RADIUS_LG,
    BORDER_W, BTN_NAVY, BTN_TEAL, BTN_RED,
)
from ui.view_registry import ViewRegistry

_POS_NAMES = dict(POSITIONS)


class HistoryView(BaseView):
    TITLE = "History"

    def build_body(self):
        head = ctk.CTkFrame(self, fg_color="transparent")
        head.pack(fill="x", padx=24, pady=(18, 6))
        ctk.CTkLabel(head, text="Saved Sessions", font=FONT_H1,
                     text_color=TXT_PRIMARY).pack(side="left")
        ctk.CTkButton(head, text="Refresh", width=90, fg_color=BTN_NAVY,
                      command=self.on_show).pack(side="right")

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(expand=True, fill="both", padx=24, pady=(0, 24))
        body.grid_columnconfigure(0, weight=3)
        body.grid_columnconfigure(1, weight=2)
        body.grid_rowconfigure(0, weight=1)

        # --- left: session list ---------------------------------------
        left = ctk.CTkFrame(body, fg_color=BG_CARD, corner_radius=RADIUS_LG)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        cols = ("date", "watch", "movement", "bph")
        self.tree = ttk.Treeview(left, columns=cols, show="headings", selectmode="browse")
        for c, t, w in (("date", "Date", 140), ("watch", "Watch", 150),
                        ("movement", "Movement", 150), ("bph", "BPH", 70)):
            self.tree.heading(c, text=t)
            self.tree.column(c, width=w, anchor="w")
        self.tree.pack(side="left", expand=True, fill="both", padx=(10, 0), pady=10)
        sb = ttk.Scrollbar(left, orient="vertical", command=self.tree.yview)
        sb.pack(side="right", fill="y", pady=10, padx=(0, 10))
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.bind("<<TreeviewSelect>>", lambda _e: self._show_detail())

        # --- right: detail + actions ----------------------------------
        right = ctk.CTkFrame(body, fg_color=BG_CARD, corner_radius=RADIUS_LG,
                             border_width=BORDER_W, border_color=BORDER_DARK)
        right.grid(row=0, column=1, sticky="nsew")
        right.grid_rowconfigure(1, weight=1)
        right.grid_columnconfigure(0, weight=1)

        self.detail_title = ctk.CTkLabel(right, text="Select a session",
                                         font=FONT_H3, text_color=TXT_PRIMARY)
        self.detail_title.grid(row=0, column=0, sticky="w", padx=14, pady=(12, 4))

        self.detail = ctk.CTkScrollableFrame(right, fg_color=BG_MAIN,
                                             corner_radius=RADIUS_LG)
        self.detail.grid(row=1, column=0, sticky="nsew", padx=12, pady=4)

        actions = ctk.CTkFrame(right, fg_color="transparent")
        actions.grid(row=2, column=0, sticky="ew", padx=12, pady=12)
        ctk.CTkButton(actions, text="Open in Trends", fg_color=BTN_TEAL,
                      command=self._open_trends).pack(side="left")
        ctk.CTkButton(actions, text="Export PDF", width=100, fg_color=BTN_NAVY,
                      command=self._export).pack(side="left", padx=(8, 0))
        ctk.CTkButton(actions, text="Delete", width=80, fg_color=BTN_RED,
                      command=self._delete).pack(side="right")

        self._sessions: dict[str, dict] = {}

    # -- data ----------------------------------------------------------
    def on_show(self):
        self.tree.delete(*self.tree.get_children())
        self._sessions.clear()
        try:
            if self.app.historian.engine is None:
                self.app.historian.connect()
            rows = self.app.historian.list_sessions()
        except Exception as exc:
            self.detail_title.configure(text=f"History unavailable: {exc}")
            return
        for s in rows:
            iid = str(s["id"])
            self._sessions[iid] = s
            date = time.strftime("%Y-%m-%d %H:%M", time.localtime(s["started_at"]))
            self.tree.insert("", "end", iid=iid,
                             values=(date, s["watch_name"] or "—",
                                     s["movement"] or "—", s["bph"]))

    def _selected_id(self):
        sel = self.tree.selection()
        return int(sel[0]) if sel else None

    def _show_detail(self):
        sid = self._selected_id()
        for w in self.detail.winfo_children():
            w.destroy()
        if sid is None:
            return
        data = self.app.historian.get_session(sid)
        if not data:
            return
        self.detail_title.configure(text=data.get("watch_name") or f"Session #{sid}")
        results = data.get("results", {})
        if not results:
            ctk.CTkLabel(self.detail, text="No positions recorded.",
                         font=FONT_BODY, text_color=TXT_SECONDARY).pack(anchor="w", pady=6)
            return

        ev = evaluate_session(results, Criteria.from_settings(self.app.settings))
        for code, r in results.items():
            name = _POS_NAMES.get(code, code)
            verdict = ev["per"].get(code, {}).get("pass")
            txt = (f"{code} · {name}   {self._verdict_tag(verdict)}\n"
                   f"   {r.get('rate_s_per_day', 0):+.1f} s/d   "
                   f"{r.get('amplitude_deg', 0):.0f}°   "
                   f"{r.get('beat_error_ms', 0):.1f} ms")
            ctk.CTkLabel(self.detail, text=txt, font=("Consolas", 12), justify="left",
                         text_color=self._verdict_color(verdict)).pack(anchor="w", pady=4)

        # --- overall verdict + spread --------------------------------
        ov = ev["overall"]
        spread = ev["spread"]
        spread_txt = "–" if spread is None else f"{spread:.1f} s/d"
        ctk.CTkLabel(self.detail,
                     text=f"Rate spread: {spread_txt}", font=FONT_BODY,
                     text_color=self._verdict_color(ev["spread_pass"])).pack(
            anchor="w", pady=(10, 0))
        ctk.CTkLabel(self.detail,
                     text=f"Overall: {self._verdict_tag(ov)}", font=FONT_H3,
                     text_color=self._verdict_color(ov)).pack(anchor="w", pady=(2, 6))

    @staticmethod
    def _verdict_tag(passed):
        if passed is None:
            return "—"
        return "PASS" if passed else "FAIL"

    @staticmethod
    def _verdict_color(passed):
        if passed is None:
            return TXT_PRIMARY
        return SUCCESS_GREEN if passed else ERROR_RED

    # -- actions -------------------------------------------------------
    def _open_trends(self):
        sid = self._selected_id()
        if sid is None:
            return
        raw = self.app.historian.get_samples(sid)
        if not raw:
            messagebox.showinfo("No trail",
                                "This session has no recorded sample trail.", parent=self)
            return
        # Normalise historian column names to the trail keys Trends expects.
        samples = [{"t": r["t"], "rate": r["rate"], "amp": r["amplitude"],
                    "be": r["beat_error"], "bph": r["bph"]} for r in raw]
        label = self._sessions.get(str(sid), {}).get("watch_name") or f"Session #{sid}"
        self.app.views["trends"].show_samples(samples, f"Saved · {label}")

    def _export(self):
        sid = self._selected_id()
        if sid is None:
            messagebox.showinfo("No session", "Select a session first.", parent=self)
            return
        data = self.app.historian.get_session(sid)
        if not data:
            return
        export_report_dialog(
            self, watch_name=data.get("watch_name") or f"Session #{sid}",
            movement_label=data.get("movement") or "", bph=data.get("bph"),
            lift_angle=data.get("lift_angle"), started_at=data.get("started_at"),
            results=data.get("results", {}), notes=data.get("notes") or "",
            criteria=Criteria.from_settings(self.app.settings))

    def _delete(self):
        sid = self._selected_id()
        if sid is None:
            return
        if not messagebox.askyesno("Delete session",
                                   f"Delete session #{sid} permanently?", parent=self):
            return
        self.app.historian.delete_session(sid)
        self.on_show()
        self.detail_title.configure(text="Select a session")
        for w in self.detail.winfo_children():
            w.destroy()


ViewRegistry.register("history", "History", "HIS", HistoryView, order=50)
