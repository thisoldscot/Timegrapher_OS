"""Session historian — SQLite store of measurement sessions and samples.

Same SQLAlchemy/SQLite approach as Sim Studio's historian. Two tables:
  sessions  — one row per watch on the bench
  samples   — periodic metric snapshots (for the trend graphs / history view)

SQLAlchemy is imported lazily so importing core/ never hard-requires it (keeps
the analyzer usable in a minimal/mobile environment that has no DB).
"""
from __future__ import annotations

import json
import time


class Historian:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.engine = None

    def connect(self) -> None:
        from sqlalchemy import create_engine  # lazy
        url = f"sqlite:///{self.db_path.replace(chr(92), '/')}"
        self.engine = create_engine(url, connect_args={"check_same_thread": False})
        with self.engine.begin() as conn:
            conn.exec_driver_sql("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    started_at REAL, watch_name TEXT, movement TEXT,
                    bph INTEGER, lift_angle REAL, notes TEXT, results_json TEXT
                )""")
            conn.exec_driver_sql("""
                CREATE TABLE IF NOT EXISTS samples (
                    session_id INTEGER, t REAL,
                    rate REAL, beat_error REAL, amplitude REAL, bph REAL
                )""")
            conn.exec_driver_sql(
                "CREATE INDEX IF NOT EXISTS idx_samples_session ON samples(session_id)")

    def save_session(self, session, samples=None) -> int:
        from sqlalchemy import text
        results = {c: vars(r) for c, r in session.results.items()}
        with self.engine.begin() as conn:
            res = conn.execute(text("""
                INSERT INTO sessions
                    (started_at, watch_name, movement, bph, lift_angle, notes, results_json)
                VALUES (:s, :w, :m, :b, :l, :n, :r)"""), {
                "s": session.started_at, "w": session.watch_name,
                "m": session.movement_label, "b": session.bph,
                "l": session.lift_angle, "n": session.notes,
                "r": json.dumps(results),
            })
            sid = res.lastrowid
            for smp in (samples or []):
                conn.execute(text("""
                    INSERT INTO samples (session_id, t, rate, beat_error, amplitude, bph)
                    VALUES (:id, :t, :rate, :be, :amp, :bph)"""),
                    {"id": sid, **smp})
        return sid

    def list_sessions(self):
        from sqlalchemy import text
        with self.engine.connect() as conn:
            rows = conn.execute(text(
                "SELECT id, started_at, watch_name, movement, bph FROM sessions "
                "ORDER BY started_at DESC")).fetchall()
        return [dict(r._mapping) for r in rows]

    def get_session(self, session_id: int):
        """Full session row (with results_json parsed) or None."""
        from sqlalchemy import text
        with self.engine.connect() as conn:
            row = conn.execute(text(
                "SELECT * FROM sessions WHERE id = :id"),
                {"id": session_id}).fetchone()
        if row is None:
            return None
        data = dict(row._mapping)
        try:
            data["results"] = json.loads(data.get("results_json") or "{}")
        except json.JSONDecodeError:
            data["results"] = {}
        return data

    def get_samples(self, session_id: int):
        """Ordered metric samples for one session (for the trend graphs)."""
        from sqlalchemy import text
        with self.engine.connect() as conn:
            rows = conn.execute(text(
                "SELECT t, rate, beat_error, amplitude, bph FROM samples "
                "WHERE session_id = :id ORDER BY t"),
                {"id": session_id}).fetchall()
        return [dict(r._mapping) for r in rows]

    def delete_session(self, session_id: int) -> None:
        from sqlalchemy import text
        with self.engine.begin() as conn:
            conn.execute(text("DELETE FROM samples WHERE session_id = :id"),
                         {"id": session_id})
            conn.execute(text("DELETE FROM sessions WHERE id = :id"),
                         {"id": session_id})
