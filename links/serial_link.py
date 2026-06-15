"""SerialLink — USB-serial transport to the ESP32 (the v1 primary link).

Owns a pyserial port and a reader thread that feeds bytes through FrameParser,
emitting BeatEvent / DeviceStatus via the BaseLink callbacks. pyserial is
imported lazily so core/ and the mock link work without it installed.
"""
from __future__ import annotations

import threading

from core.beat_event import BeatEvent, DeviceStatus

from .base_link import BaseLink
from .protocol import FrameParser, T_BEAT, T_STATUS, encode_command


class SerialLink(BaseLink):
    def __init__(self, port: str, baud: int = 921600):
        self.port = port
        self.baud = baud
        self._serial = None
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()

    @property
    def is_open(self) -> bool:
        return self._serial is not None and getattr(self._serial, "is_open", False)

    def open(self) -> None:
        import serial  # lazy: pyserial
        try:
            self._serial = serial.Serial(self.port, self.baud, timeout=0.1)
        except (serial.SerialException, PermissionError, OSError) as exc:
            # Windows COM ports are exclusive: the most common failure is the
            # port already being held by another program (the Arduino IDE's
            # Serial Monitor, PuTTY, a previous app instance...). pyserial
            # surfaces that as "Access is denied" / errno 13 — translate it into
            # something the user can act on instead of a raw traceback.
            msg = str(exc)
            if "Access is denied" in msg or "PermissionError(13" in msg \
                    or getattr(exc, "errno", None) == 13:
                raise ConnectionError(
                    f"{self.port} is in use by another program "
                    f"(close the Arduino Serial Monitor / PuTTY, then retry)."
                ) from exc
            if "FileNotFoundError" in msg or "could not open port" in msg \
                    or getattr(exc, "errno", None) == 2:
                raise ConnectionError(
                    f"{self.port} not found — check the cable and the selected port."
                ) from exc
            raise ConnectionError(f"Could not open {self.port}: {exc}") from exc
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="SerialLink", daemon=True)
        self._thread.start()

    def close(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=1.0)
            self._thread = None
        if self._serial:
            try:
                self._serial.close()
            except Exception:
                pass
            self._serial = None

    def set_gain(self, gain: int) -> None:
        self._write(encode_command(set_gain=int(gain)))

    def subscribe_waveform(self, enabled: bool) -> None:
        self._write(encode_command(waveform=bool(enabled)))

    def ping(self) -> None:
        self._write(encode_command(ping=1))

    def _write(self, data: bytes) -> None:
        if self.is_open:
            try:
                self._serial.write(data)
            except Exception:
                pass

    def _run(self) -> None:
        parser = FrameParser()
        while not self._stop.is_set():
            try:
                chunk = self._serial.read(4096)
            except Exception:
                break
            if not chunk:
                continue
            for ftype, value in parser.feed(chunk):
                if ftype == T_BEAT and isinstance(value, BeatEvent):
                    self._emit_beat(value)
                elif ftype == T_STATUS and isinstance(value, DeviceStatus):
                    self._emit_status(value)
