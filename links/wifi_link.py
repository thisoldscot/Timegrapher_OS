"""WifiLink — TCP-socket transport to the ESP32 (shared with the mobile app).

Stub for v1: the framing/protocol is identical to SerialLink, only the byte
source differs (a TCP socket instead of a serial port). Fill in connect/read
when the firmware Wi-Fi server lands. Kept registered so the UI dropdown and the
mobile build can target it without code changes elsewhere.
"""
from __future__ import annotations

import socket
import threading

from .base_link import BaseLink
from .protocol import FrameParser, T_BEAT, T_STATUS, encode_command


class WifiLink(BaseLink):
    def __init__(self, address: str, port: int = 3333):
        self.address = address
        self.port = port
        self._sock: socket.socket | None = None
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()

    @property
    def is_open(self) -> bool:
        return self._sock is not None

    def open(self) -> None:
        self._sock = socket.create_connection((self.address, self.port), timeout=5.0)
        self._sock.settimeout(0.2)
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="WifiLink", daemon=True)
        self._thread.start()

    def close(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=1.0)
            self._thread = None
        if self._sock:
            try:
                self._sock.close()
            finally:
                self._sock = None

    def set_gain(self, gain: int) -> None:
        self._send(encode_command(set_gain=int(gain)))

    def _send(self, data: bytes) -> None:
        if self._sock:
            try:
                self._sock.sendall(data)
            except OSError:
                pass

    def _run(self) -> None:
        parser = FrameParser()
        while not self._stop.is_set():
            try:
                chunk = self._sock.recv(4096)
            except socket.timeout:
                continue
            except OSError:
                break
            if not chunk:
                break
            for ftype, value in parser.feed(chunk):
                if ftype == T_BEAT:
                    self._emit_beat(value)
                elif ftype == T_STATUS:
                    self._emit_status(value)
