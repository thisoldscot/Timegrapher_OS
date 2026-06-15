"""App settings persistence — JSON round-trip in the user config dir.

Mirrors the role of utils/config_manager.py in the sibling apps: a single dict
loaded at start and saved on change, holding the last device, gain, lift angle,
BPH mode, and window geometry.
"""
from __future__ import annotations

import json
import os

from core.criteria import DEFAULT_CRITERIA

APP_DIR = os.path.join(os.path.expanduser("~"), ".timegrapher_studio")
CONFIG_PATH = os.path.join(APP_DIR, "config.json")
MOVEMENTS_USER_PATH = os.path.join(APP_DIR, "movements_user.json")
HISTORY_DB_PATH = os.path.join(APP_DIR, "history.db")

# Stock rolling-average windows (seconds). Editable from Settings.
TIMEBASE_DEFAULTS = [10, 30, 60, 120, 300]

DEFAULTS = {
    "link_kind": "Mock (Demo)",
    "link_address": "",
    "gain": 32,
    "lift_angle": 52.0,
    "bph_mode": "auto",          # "auto" or an int
    "window_seconds": 6.0,
    "selected_movement": "",     # label of the movement in use this session
    "watch_name": "",            # current bench watch label
    "avg_timebases": list(TIMEBASE_DEFAULTS),   # rolling-average windows (s)
    "avg_default": 30,           # default window selected on the Live view
    "trends_window": 0,          # Trends X-span in s; 0 = whole session
    "stabilize_seconds": 15,     # auto-run settle time before each capture
    **DEFAULT_CRITERIA,          # pass/fail tolerances (tol_rate, tol_be_max, …)
    "window_state": {},          # geometry, sidebar width…
}


def format_timebase(seconds: int) -> str:
    """Human label for a time-base in seconds: 30 -> "30 s", 120 -> "2 min"."""
    s = int(round(seconds))
    if s >= 60 and s % 60 == 0:
        return f"{s // 60} min"
    return f"{s} s"


def parse_timebases(text: str) -> list[int]:
    """Parse a free-text list like "10s, 30, 1 min, 2min" into sorted seconds.

    Accepts bare numbers (seconds), an "s" suffix, or an "m"/"min" suffix.
    Invalid tokens are skipped; the result is de-duplicated and sorted.
    """
    out: set[int] = set()
    for tok in text.replace(";", ",").split(","):
        t = tok.strip().lower()
        if not t:
            continue
        try:
            if t.endswith("min"):
                val = float(t[:-3]) * 60
            elif t.endswith("m"):
                val = float(t[:-1]) * 60
            elif t.endswith("s"):
                val = float(t[:-1])
            else:
                val = float(t)
        except ValueError:
            continue
        sec = int(round(val))
        if sec > 0:
            out.add(sec)
    return sorted(out)


class SettingsStore:
    def __init__(self, path: str = CONFIG_PATH):
        self.path = path
        self.data = dict(DEFAULTS)
        self.load()

    def load(self) -> None:
        try:
            with open(self.path, "r", encoding="utf-8") as fh:
                loaded = json.load(fh)
            self.data = {**DEFAULTS, **loaded}
        except (OSError, json.JSONDecodeError):
            self.data = dict(DEFAULTS)

    def save(self) -> None:
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as fh:
            json.dump(self.data, fh, indent=2)

    def get(self, key, default=None):
        return self.data.get(key, default)

    def set(self, key, value) -> None:
        self.data[key] = value
