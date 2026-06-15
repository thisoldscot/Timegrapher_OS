"""MovementsView — browse and curate the movement database.

The grid lists every movement (maker / caliber → bph, lift angle). The toolbar
adds, edits, deletes, and CSV-imports/exports records, and selects the movement
for the current session (which pins its lift angle + BPH and shows it in the
header). Double-clicking a row selects it.
"""
from __future__ import annotations

from tkinter import ttk, filedialog, messagebox

import customtkinter as ctk

from core.movement_db import Movement
from core.constants import STANDARD_BPH
from ui.base_view import BaseView
from ui.theme import (
    BG_CARD, BG_MAIN, BORDER_DARK, TXT_PRIMARY, TXT_SECONDARY, BRAND_CYAN,
    SUCCESS_GREEN, FONT_H1, FONT_H3, FONT_BODY, RADIUS_LG, BTN_NAVY, BTN_TEAL,
    BTN_RED,
)
from ui.view_registry import ViewRegistry

_ALL = "All makers"


class MovementsView(BaseView):
    TITLE = "Movements"

    def build_body(self):
        ctk.CTkLabel(self, text="Movement Database", font=FONT_H1,
                     text_color=TXT_PRIMARY).pack(anchor="w", padx=24, pady=(18, 6))

        # --- toolbar --------------------------------------------------
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.pack(fill="x", padx=24, pady=(0, 8))
        ctk.CTkButton(bar, text="Use for Session", width=130, fg_color=BTN_TEAL,
                      command=self._use_selected).pack(side="left")
        ctk.CTkButton(bar, text="New", width=70, fg_color=BTN_NAVY,
                      command=self._new).pack(side="left", padx=(10, 0))
        ctk.CTkButton(bar, text="Edit", width=70, fg_color=BTN_NAVY,
                      command=self._edit).pack(side="left", padx=6)
        ctk.CTkButton(bar, text="Delete", width=70, fg_color=BTN_RED,
                      command=self._delete).pack(side="left")
        ctk.CTkButton(bar, text="Import CSV", width=100, fg_color=BTN_NAVY,
                      command=self._import).pack(side="right")
        ctk.CTkButton(bar, text="Export CSV", width=100, fg_color=BTN_NAVY,
                      command=self._export).pack(side="right", padx=(0, 8))

        # --- filters --------------------------------------------------
        flt = ctk.CTkFrame(self, fg_color="transparent")
        flt.pack(fill="x", padx=24, pady=(0, 8))
        ctk.CTkLabel(flt, text="Maker", font=FONT_BODY,
                     text_color=TXT_SECONDARY).pack(side="left", padx=(0, 6))
        self.filter_maker = ctk.StringVar(value=_ALL)
        self.maker_box = ctk.CTkComboBox(flt, width=200, variable=self.filter_maker,
                                         values=[_ALL],
                                         command=lambda _=None: self._reload())
        self.maker_box.pack(side="left")
        ctk.CTkLabel(flt, text="Caliber", font=FONT_BODY,
                     text_color=TXT_SECONDARY).pack(side="left", padx=(16, 6))
        self.filter_caliber = ctk.StringVar()
        cal_entry = ctk.CTkEntry(flt, textvariable=self.filter_caliber, width=200,
                                 placeholder_text="search…")
        cal_entry.pack(side="left")
        cal_entry.bind("<KeyRelease>", lambda _e: self._reload())
        ctk.CTkButton(flt, text="Clear", width=70, fg_color=BTN_NAVY,
                      command=self._clear_filters).pack(side="left", padx=(10, 0))
        self.count_lbl = ctk.CTkLabel(flt, text="", font=FONT_BODY,
                                      text_color=TXT_SECONDARY)
        self.count_lbl.pack(side="right")

        # --- table ----------------------------------------------------
        card = ctk.CTkFrame(self, fg_color=BG_CARD, corner_radius=RADIUS_LG)
        card.pack(expand=True, fill="both", padx=24, pady=(0, 24))

        cols = ("maker", "caliber", "bph", "lift")
        self.tree = ttk.Treeview(card, columns=cols, show="headings", selectmode="browse")
        for c, t, w in (("maker", "Maker", 180), ("caliber", "Caliber", 220),
                        ("bph", "BPH", 90), ("lift", "Lift °", 90)):
            self.tree.heading(c, text=t)
            self.tree.column(c, width=w, anchor="w")
        self.tree.tag_configure("selected", foreground=BRAND_CYAN)
        self.tree.pack(side="left", expand=True, fill="both", padx=(10, 0), pady=10)
        sb = ttk.Scrollbar(card, orient="vertical", command=self.tree.yview)
        sb.pack(side="right", fill="y", pady=10, padx=(0, 10))
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.bind("<Double-1>", lambda _e: self._use_selected())

        self._reload()

    # -- helpers --------------------------------------------------------
    def on_show(self):
        self._reload()

    def _clear_filters(self):
        self.filter_maker.set(_ALL)
        self.filter_caliber.set("")
        self._reload()

    def _reload(self):
        all_movements = self.app.movement_db.all()
        # Keep the maker dropdown in sync with the database.
        makers = [_ALL] + sorted({m.maker for m in all_movements}, key=str.lower)
        self.maker_box.configure(values=makers)
        if self.filter_maker.get() not in makers:
            self.filter_maker.set(_ALL)

        maker = self.filter_maker.get()
        needle = self.filter_caliber.get().strip().lower()

        self.tree.delete(*self.tree.get_children())
        sel = getattr(self.app.current_movement, "label", None)
        shown = 0
        for m in all_movements:
            if maker != _ALL and m.maker != maker:
                continue
            if needle and needle not in m.caliber.lower():
                continue
            tag = ("selected",) if m.label == sel else ()
            self.tree.insert("", "end", iid=m.label,
                             values=(m.maker, m.caliber, m.bph, m.lift_angle), tags=tag)
            shown += 1
        total = len(all_movements)
        self.count_lbl.configure(
            text=f"{shown} of {total}" if shown != total else f"{total} movements")

    def _selected_movement(self):
        sel = self.tree.selection()
        if not sel:
            return None
        return self.app.movement_db.find(sel[0])

    # -- actions --------------------------------------------------------
    def _use_selected(self):
        m = self._selected_movement()
        if m:
            self.app.select_movement(m)
            self._reload()

    def _new(self):
        MovementDialog(self, "New Movement", None, self._save)

    def _edit(self):
        m = self._selected_movement()
        if m:
            MovementDialog(self, f"Edit · {m.label}", m, self._save)

    def _save(self, movement: Movement):
        self.app.movement_db.add(movement)
        # If we just edited the in-use movement, re-pin its values.
        if getattr(self.app.current_movement, "label", None) == movement.label:
            self.app.select_movement(movement)
        self._reload()

    def _delete(self):
        m = self._selected_movement()
        if not m:
            return
        if messagebox.askyesno("Delete movement",
                               f"Remove “{m.label}” from the database?", parent=self):
            self.app.movement_db.remove(m.label)
            if getattr(self.app.current_movement, "label", None) == m.label:
                self.app.select_movement(None)
            self._reload()

    def _import(self):
        path = filedialog.askopenfilename(
            parent=self, title="Import movements CSV",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")])
        if not path:
            return
        try:
            n = self.app.movement_db.import_csv(path)
        except OSError as exc:
            messagebox.showerror("Import failed", str(exc), parent=self)
            return
        messagebox.showinfo("Import complete",
                            f"Imported / updated {n} movement(s).", parent=self)
        self._reload()

    def _export(self):
        path = filedialog.asksaveasfilename(
            parent=self, title="Export movements CSV", defaultextension=".csv",
            initialfile="movements.csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")])
        if not path:
            return
        try:
            n = self.app.movement_db.export_csv(path)
        except OSError as exc:
            messagebox.showerror("Export failed", str(exc), parent=self)
            return
        messagebox.showinfo("Export complete", f"Wrote {n} movement(s).", parent=self)


class MovementDialog(ctk.CTkToplevel):
    """Modal add/edit form for a single movement record."""

    def __init__(self, parent, title, movement, on_save):
        super().__init__(parent)
        self.on_save = on_save
        self.title(title)
        self.configure(fg_color=BG_MAIN)
        self.geometry("420x320")
        self.transient(parent.winfo_toplevel())
        self.resizable(False, False)

        card = ctk.CTkFrame(self, fg_color=BG_CARD, corner_radius=RADIUS_LG)
        card.pack(expand=True, fill="both", padx=16, pady=16)
        card.grid_columnconfigure(1, weight=1)

        self.maker = ctk.StringVar(value=movement.maker if movement else "")
        self.caliber = ctk.StringVar(value=movement.caliber if movement else "")
        self.bph = ctk.StringVar(value=str(movement.bph) if movement else "28800")
        self.lift_var = ctk.StringVar(value=str(movement.lift_angle) if movement else "52")

        self._field(card, 0, "Maker", self.maker)
        self._field(card, 1, "Caliber", self.caliber)
        self._bph_field(card, 2)
        self._field(card, 3, "Lift angle (°)", self.lift_var)

        self.err = ctk.CTkLabel(card, text="", font=FONT_BODY, text_color="#E74C3C")
        self.err.grid(row=4, column=0, columnspan=2, sticky="w", padx=16)

        btns = ctk.CTkFrame(card, fg_color="transparent")
        btns.grid(row=5, column=0, columnspan=2, sticky="e", padx=16, pady=(8, 12))
        ctk.CTkButton(btns, text="Cancel", width=90, fg_color=BTN_NAVY,
                      command=self.destroy).pack(side="left", padx=(0, 8))
        ctk.CTkButton(btns, text="Save", width=90, fg_color=BTN_TEAL,
                      command=self._submit).pack(side="left")

        self.after(80, self._raise)

    def _raise(self):
        self.grab_set()
        self.lift()        # bring to front
        self.focus_force()

    def _field(self, parent, r, label, var):
        ctk.CTkLabel(parent, text=label, font=FONT_H3, text_color=TXT_PRIMARY).grid(
            row=r, column=0, sticky="w", padx=16, pady=10)
        ctk.CTkEntry(parent, textvariable=var, width=200).grid(
            row=r, column=1, sticky="ew", padx=16, pady=10)

    def _bph_field(self, parent, r):
        ctk.CTkLabel(parent, text="BPH", font=FONT_H3, text_color=TXT_PRIMARY).grid(
            row=r, column=0, sticky="w", padx=16, pady=10)
        ctk.CTkComboBox(parent, variable=self.bph, width=200,
                        values=[str(b) for b in STANDARD_BPH]).grid(
            row=r, column=1, sticky="ew", padx=16, pady=10)

    def _submit(self):
        maker = self.maker.get().strip()
        caliber = self.caliber.get().strip()
        if not maker or not caliber:
            self.err.configure(text="Maker and caliber are required.")
            return
        try:
            bph = int(float(self.bph.get()))
            lift = float(self.lift_var.get())
        except ValueError:
            self.err.configure(text="BPH and lift angle must be numbers.")
            return
        self.on_save(Movement(maker=maker, caliber=caliber, bph=bph, lift_angle=lift))
        self.destroy()


ViewRegistry.register("movements", "Movements", "MOV", MovementsView, order=60)
