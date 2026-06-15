"""Round-trip and resilience checks for the wire protocol."""
from core.beat_event import BeatEvent

from links.protocol import (
    FrameParser, crc16, encode_beat, encode_command, T_BEAT, T_CMD,
)


def test_beat_roundtrip():
    ev = BeatEvent(seq=42, onset_ticks=123456789, dt_ticks=900, level=30000)
    parser = FrameParser()
    out = parser.feed(encode_beat(ev))
    assert len(out) == 1
    ftype, value = out[0]
    assert ftype == T_BEAT
    assert value == ev


def test_command_roundtrip():
    parser = FrameParser()
    out = parser.feed(encode_command(set_gain=40))
    assert out[0][0] == T_CMD
    assert out[0][1] == {"set_gain": 40}


def test_split_across_reads():
    ev = BeatEvent(seq=1, onset_ticks=999, dt_ticks=10, level=5)
    data = encode_beat(ev)
    parser = FrameParser()
    assert parser.feed(data[:3]) == []
    out = parser.feed(data[3:])
    assert out[0][1] == ev


def test_resync_after_garbage():
    ev = BeatEvent(seq=7, onset_ticks=7, dt_ticks=7, level=7)
    parser = FrameParser()
    out = parser.feed(b"\x00\x11\x22" + encode_beat(ev))
    assert out[0][1] == ev


def test_corrupt_crc_dropped():
    ev = BeatEvent(seq=7, onset_ticks=7, dt_ticks=7, level=7)
    data = bytearray(encode_beat(ev))
    data[5] ^= 0xFF   # corrupt a payload byte
    parser = FrameParser()
    assert parser.feed(bytes(data)) == []


def test_two_frames_one_feed():
    a = BeatEvent(seq=1, onset_ticks=1, dt_ticks=1, level=1)
    b = BeatEvent(seq=2, onset_ticks=2, dt_ticks=2, level=2)
    parser = FrameParser()
    out = parser.feed(encode_beat(a) + encode_beat(b))
    assert [v.seq for _, v in out] == [1, 2]


def test_crc16_known_vector():
    # CRC-16/CCITT-FALSE of "123456789" is 0x29B1.
    assert crc16(b"123456789") == 0x29B1
