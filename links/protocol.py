"""Wire protocol: framing + encode/decode of device frames.

Frame layout (transport-agnostic — same bytes over serial, TCP, BLE):

    0xA5  type:u8  len:u16(LE)  payload[len]  crc16:u16(LE)

Hot-path BEAT frames are packed binary (little-endian); control frames (CMD,
HELLO) carry small JSON. See firmware/PROTOCOL.md for the authoritative spec.
"""
from __future__ import annotations

import json
import struct

from core.beat_event import BeatEvent, DeviceStatus

SOF = 0xA5

T_HELLO = 0x01
T_BEAT = 0x02
T_WAVE = 0x03
T_STATUS = 0x04
T_CMD = 0x10

# BEAT payload: seq:u32, onset_ticks:u64, dt_ticks:u16, level:u16
_BEAT = struct.Struct("<IQHH")
# STATUS payload: gain:u8, flags:u8, temp_c_x100:i16, sample_rate:u32
_STATUS = struct.Struct("<BBhI")


def crc16(data: bytes) -> int:
    """CRC-16/CCITT-FALSE (poly 0x1021, init 0xFFFF) — matches firmware."""
    crc = 0xFFFF
    for b in data:
        crc ^= b << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) & 0xFFFF if (crc & 0x8000) else (crc << 1) & 0xFFFF
    return crc


def frame(ftype: int, payload: bytes) -> bytes:
    body = bytes([SOF, ftype]) + struct.pack("<H", len(payload)) + payload
    return body + struct.pack("<H", crc16(payload))


def encode_beat(ev: BeatEvent) -> bytes:
    return frame(T_BEAT, _BEAT.pack(ev.seq, ev.onset_ticks, ev.dt_ticks, ev.level))


def encode_command(**kwargs) -> bytes:
    """Host→device control frame, e.g. encode_command(set_gain=40)."""
    return frame(T_CMD, json.dumps(kwargs).encode("utf-8"))


def decode_payload(ftype: int, payload: bytes):
    """Turn a verified payload into a value object, or None if unknown."""
    if ftype == T_BEAT:
        seq, onset, dt, level = _BEAT.unpack(payload)
        return BeatEvent(seq=seq, onset_ticks=onset, dt_ticks=dt, level=level)
    if ftype == T_STATUS:
        gain, flags, temp, sr = _STATUS.unpack(payload)
        return DeviceStatus(gain=gain, clock_locked=bool(flags & 1),
                            temperature_c=temp / 100.0, sample_rate=sr)
    if ftype in (T_HELLO, T_CMD):
        try:
            return json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return None
    return None


class FrameParser:
    """Incremental byte-stream parser. Feed bytes, get back (type, value) pairs.

    Resilient to partial reads and resyncs on a bad CRC / lost SOF.
    """

    def __init__(self):
        self._buf = bytearray()

    def feed(self, chunk: bytes):
        self._buf.extend(chunk)
        out = []
        while True:
            # Resync to the next SOF.
            sof = self._buf.find(SOF)
            if sof < 0:
                self._buf.clear()
                break
            if sof > 0:
                del self._buf[:sof]
            if len(self._buf) < 4:
                break
            length = self._buf[2] | (self._buf[3] << 8)
            total = 4 + length + 2
            if len(self._buf) < total:
                break
            ftype = self._buf[1]
            payload = bytes(self._buf[4:4 + length])
            crc_rx = self._buf[4 + length] | (self._buf[4 + length + 1] << 8)
            del self._buf[:total]
            if crc_rx != crc16(payload):
                continue   # corrupt frame — drop and keep scanning
            value = decode_payload(ftype, payload)
            if value is not None:
                out.append((ftype, value))
        return out
