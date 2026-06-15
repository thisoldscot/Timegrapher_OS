"""Movement database — caliber → (lift angle, bph) lookup.

Bundled defaults live in movements.json next to this file. A user-editable copy
is kept in the app config dir; user entries override bundled ones of the same
label, so edits and additions survive upgrades. The set can also be grown from /
dumped to CSV (maker, caliber, bph, lift_angle).
"""
from __future__ import annotations

import csv
import json
import os
from dataclasses import asdict, dataclass

_BUNDLED = os.path.join(os.path.dirname(__file__), "movements.json")
CSV_FIELDS = ("maker", "caliber", "bph", "lift_angle")


@dataclass
class Movement:
    maker: str
    caliber: str
    bph: int
    lift_angle: float

    @property
    def label(self) -> str:
        return f"{self.maker} {self.caliber}"


class MovementDB:
    def __init__(self, user_path: str | None = None):
        self.user_path = user_path
        self._movements: list[Movement] = []
        self.load()

    # -- loading --------------------------------------------------------
    def load(self) -> None:
        by_label: dict[str, Movement] = {}
        for d in self._read(_BUNDLED):
            m = Movement(**d)
            by_label[m.label] = m
        if self.user_path and os.path.exists(self.user_path):
            for d in self._read(self.user_path):
                try:
                    m = Movement(maker=d["maker"], caliber=d["caliber"],
                                 bph=int(d["bph"]), lift_angle=float(d["lift_angle"]))
                except (KeyError, ValueError, TypeError):
                    continue
                by_label[m.label] = m   # user overrides bundled
        self._movements = self._sorted(by_label.values())

    @staticmethod
    def _read(path: str) -> list[dict]:
        try:
            with open(path, "r", encoding="utf-8") as fh:
                return json.load(fh)
        except (OSError, json.JSONDecodeError):
            return []

    @staticmethod
    def _sorted(movements):
        return sorted(movements, key=lambda m: (m.maker.lower(), m.caliber.lower()))

    # -- queries --------------------------------------------------------
    def all(self) -> list[Movement]:
        return list(self._movements)

    def find(self, label: str) -> Movement | None:
        return next((m for m in self._movements if m.label == label), None)

    # -- mutation -------------------------------------------------------
    def _upsert(self, m: Movement) -> None:
        self._movements = [x for x in self._movements if x.label != m.label]
        self._movements.append(m)

    def add(self, m: Movement) -> None:
        """Add or replace a movement (matched by label) and persist."""
        self._upsert(m)
        self._movements = self._sorted(self._movements)
        self.save_user()

    def remove(self, label: str) -> None:
        """Drop a movement and persist. (A bundled entry reappears on reload.)"""
        self._movements = [x for x in self._movements if x.label != label]
        self.save_user()

    def save_user(self) -> None:
        if not self.user_path:
            return
        os.makedirs(os.path.dirname(self.user_path), exist_ok=True)
        with open(self.user_path, "w", encoding="utf-8") as fh:
            json.dump([asdict(m) for m in self._movements], fh, indent=2)

    # -- CSV interchange ------------------------------------------------
    def import_csv(self, path: str) -> int:
        """Merge movements from a CSV (header: maker,caliber,bph,lift_angle).

        Returns the number of valid rows imported. Existing labels are updated.
        """
        added = 0
        with open(path, "r", newline="", encoding="utf-8-sig") as fh:
            for row in csv.DictReader(fh):
                try:
                    m = Movement(
                        maker=str(row["maker"]).strip(),
                        caliber=str(row["caliber"]).strip(),
                        bph=int(float(row["bph"])),
                        lift_angle=float(row["lift_angle"]),
                    )
                except (KeyError, ValueError, TypeError, AttributeError):
                    continue
                if not m.maker and not m.caliber:
                    continue
                self._upsert(m)
                added += 1
        self._movements = self._sorted(self._movements)
        self.save_user()
        return added

    def export_csv(self, path: str) -> int:
        """Write the whole database to CSV. Returns the row count."""
        with open(path, "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(CSV_FIELDS)
            for m in self._movements:
                w.writerow([m.maker, m.caliber, m.bph, m.lift_angle])
        return len(self._movements)
