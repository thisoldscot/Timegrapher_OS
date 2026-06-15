"""Shared 'export PDF report' helper — file dialog + write + user feedback.

Both the Positions view (latest run) and the History view (any saved record)
funnel through here so the save dialog, error handling and the normalised data
shape stay in one place.
"""
from __future__ import annotations

import os
import re
import time
from tkinter import filedialog, messagebox

from core.report import write_session_report


def _safe(name: str) -> str:
    base = re.sub(r"[^A-Za-z0-9._ -]", "_", (name or "watch").strip()) or "watch"
    return base[:48]


def export_report_dialog(parent, *, watch_name, movement_label, bph, lift_angle,
                         started_at, results, notes="", criteria=None) -> bool:
    """Prompt for a path and write the PDF. Returns True on success."""
    if not results:
        messagebox.showinfo("Nothing to export",
                            "Capture at least one position first.", parent=parent)
        return False

    stamp = time.strftime("%Y%m%d", time.localtime(started_at or time.time()))
    path = filedialog.asksaveasfilename(
        parent=parent, title="Export PDF report", defaultextension=".pdf",
        initialfile=f"{_safe(watch_name)}_{stamp}.pdf",
        filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")])
    if not path:
        return False

    try:
        write_session_report(
            path, watch_name=watch_name, movement_label=movement_label,
            bph=bph, lift_angle=lift_angle, started_at=started_at,
            results=results, notes=notes, criteria=criteria)
    except Exception as exc:   # surface reportlab / IO failures plainly
        messagebox.showerror("Export failed", str(exc), parent=parent)
        return False

    if messagebox.askyesno("Report saved",
                           f"Saved report to:\n{path}\n\nOpen it now?", parent=parent):
        try:
            os.startfile(path)   # Windows; harmless to guard
        except (AttributeError, OSError):
            pass
    return True
