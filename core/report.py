"""PDF measurement report — one watch, its positions, and the run averages.

Tk-free and self-contained (reportlab imported lazily) so it can be reused by the
future mobile build. Feed it a normalised session dict via ``write_session_report``;
both the live session and a saved historian record map onto the same shape.
"""
from __future__ import annotations

import math
import time

from core.criteria import evaluate_reading, evaluate_session
from core.session import POSITIONS

_POS_NAMES = dict(POSITIONS)
_POS_ORDER = [code for code, _ in POSITIONS]


def _verdict_text(passed) -> str:
    return "—" if passed is None else ("PASS" if passed else "FAIL")


def _fmt(value, spec: str, dash: str = "—") -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return dash
    return format(value, spec)


def _averages(results: dict) -> dict:
    def mean(key):
        vals = [r.get(key) for r in results.values()]
        clean = [v for v in vals if v is not None and not (isinstance(v, float) and math.isnan(v))]
        return (sum(clean) / len(clean)) if clean else None
    return {
        "rate_s_per_day": mean("rate_s_per_day"),
        "amplitude_deg": mean("amplitude_deg"),
        "beat_error_ms": mean("beat_error_ms"),
    }


def _ordered(results: dict):
    """Yield (code, result) in canonical position order, extras last."""
    seen = set()
    for code in _POS_ORDER:
        if code in results:
            seen.add(code)
            yield code, results[code]
    for code, r in results.items():
        if code not in seen:
            yield code, r


def write_session_report(path: str, *, watch_name: str, movement_label: str,
                         bph, lift_angle, started_at: float, results: dict,
                         notes: str = "", criteria=None) -> str:
    """Render a one-page PDF report to ``path`` and return the path.

    ``results`` maps a position code to a dict with rate_s_per_day,
    amplitude_deg, beat_error_ms and (optionally) captured_at. When ``criteria``
    (a core.criteria.Criteria) is given, a pass/fail column, an overall verdict
    and the tolerances used are added.
    """
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle)

    styles = getSampleStyleSheet()
    title = ParagraphStyle("tg_title", parent=styles["Title"], fontSize=20,
                           textColor=colors.HexColor("#0E7C86"), spaceAfter=2)
    sub = ParagraphStyle("tg_sub", parent=styles["Normal"], fontSize=9,
                         textColor=colors.HexColor("#666666"))
    h2 = ParagraphStyle("tg_h2", parent=styles["Heading2"], fontSize=12,
                        textColor=colors.HexColor("#222222"), spaceBefore=10, spaceAfter=4)

    now = time.time()
    story = [
        Paragraph("Timegrapher Studio — Measurement Report", title),
        Paragraph(watch_name or "Unnamed watch", styles["Heading3"]),
        Spacer(1, 4),
    ]

    # --- summary block (movement + timestamps) -----------------------
    cap_dt = (time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(started_at))
              if started_at else "—")
    info = [
        ["Movement", movement_label or "—", "Beat rate", f"{bph} bph" if bph else "—"],
        ["Lift angle", _fmt(float(lift_angle) if lift_angle is not None else None, ".0f") + "°",
         "Positions", str(len(results))],
        ["Captured", cap_dt, "Report created",
         time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(now))],
    ]
    info_tbl = Table(info, colWidths=[28 * mm, 62 * mm, 30 * mm, 50 * mm])
    info_tbl.setStyle(TableStyle([
        ("FONT", (0, 0), (-1, -1), "Helvetica", 9),
        ("FONT", (0, 0), (0, -1), "Helvetica-Bold", 9),
        ("FONT", (2, 0), (2, -1), "Helvetica-Bold", 9),
        ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#666666")),
        ("TEXTCOLOR", (2, 0), (2, -1), colors.HexColor("#666666")),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
    ]))
    story += [info_tbl, Paragraph("Captured positions", h2)]

    # --- per-position table ------------------------------------------
    verdict = evaluate_session(results, criteria) if criteria is not None else None
    green = colors.HexColor("#1E8449")
    red = colors.HexColor("#C0392B")

    header = ["Position", "Rate (s/d)", "Amplitude (°)", "Beat error (ms)", "Time"]
    if verdict is not None:
        header.append("Result")
    data = [header]
    cell_colors = []        # (col, row, color) overrides for pass/fail text
    for code, r in _ordered(results):
        name = _POS_NAMES.get(code, code)
        cap = r.get("captured_at")
        row = [
            f"{code} · {name}",
            _fmt(r.get("rate_s_per_day"), "+.1f"),
            _fmt(r.get("amplitude_deg"), ".0f"),
            _fmt(r.get("beat_error_ms"), ".1f"),
            time.strftime("%H:%M:%S", time.localtime(cap)) if cap else "—",
        ]
        if verdict is not None:
            p = verdict["per"].get(code, {})
            row.append(_verdict_text(p.get("pass")))
            ridx = len(data)
            # colour each metric cell + the result cell by its own check
            for col, key in ((1, "rate"), (2, "amplitude"), (3, "beat_error")):
                chk = p.get("checks", {}).get(key)
                if chk is not None:
                    cell_colors.append((col, ridx, green if chk else red))
            if p.get("pass") is not None:
                cell_colors.append((5, ridx, green if p["pass"] else red))
        data.append(row)

    avg = _averages(results)
    avg_row = [
        "Average",
        _fmt(avg["rate_s_per_day"], "+.1f"),
        _fmt(avg["amplitude_deg"], ".0f"),
        _fmt(avg["beat_error_ms"], ".1f"),
        "",
    ]
    if verdict is not None:
        avg_row.append(_verdict_text(verdict["overall"]))
        if verdict["overall"] is not None:
            cell_colors.append((5, len(data), green if verdict["overall"] else red))
    data.append(avg_row)

    widths = ([50 * mm, 27 * mm, 29 * mm, 30 * mm, 18 * mm, 20 * mm]
              if verdict is not None else [55 * mm, 30 * mm, 32 * mm, 33 * mm, 20 * mm])
    tbl = Table(data, colWidths=widths, repeatRows=1)
    style = [
        ("FONT", (0, 0), (-1, -1), "Helvetica", 9),
        ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 9),
        ("FONT", (0, -1), (-1, -1), "Helvetica-Bold", 9),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0E7C86")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#EAF4F5")),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("ALIGN", (0, 0), (0, -1), "LEFT"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, colors.HexColor("#F5F5F5")]),
        ("LINEABOVE", (0, -1), (-1, -1), 0.6, colors.HexColor("#0E7C86")),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#CCCCCC")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    for col, row, color in cell_colors:
        style.append(("TEXTCOLOR", (col, row), (col, row), color))
    tbl.setStyle(TableStyle(style))
    story.append(tbl)

    # --- verdict + criteria summary ----------------------------------
    if verdict is not None:
        ov = verdict["overall"]
        ov_color = green if ov else (red if ov is False else colors.HexColor("#666666"))
        result = ParagraphStyle("tg_result", parent=styles["Heading2"], fontSize=13,
                                textColor=ov_color, spaceBefore=10, spaceAfter=2)
        sp = verdict["spread"]
        sp_txt = "—" if sp is None else f"{sp:.1f} s/d"
        story += [
            Paragraph(f"Overall result: {_verdict_text(ov)}", result),
            Paragraph(
                f"Rate spread {sp_txt} (limit ≤ {criteria.spread_max:.0f}). "
                f"Criteria — rate {criteria.rate_target:+.0f} ± {criteria.rate_tol:.0f} s/d, "
                f"beat error ≤ {criteria.be_max:.2f} ms, "
                f"amplitude {criteria.amp_min:.0f}–{criteria.amp_max:.0f}°.", sub),
        ]

    if notes:
        story += [Paragraph("Notes", h2), Paragraph(notes, styles["Normal"])]

    story += [Spacer(1, 12),
              Paragraph("Generated by Timegrapher Studio · "
                        "rate referenced to a DS3231 ±2 ppm time base.", sub)]

    doc = SimpleDocTemplate(path, pagesize=A4, title=f"Report — {watch_name or 'watch'}",
                            leftMargin=18 * mm, rightMargin=18 * mm,
                            topMargin=16 * mm, bottomMargin=16 * mm)
    doc.build(story)
    return path
