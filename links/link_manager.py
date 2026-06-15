"""Link registry — maps a UI-facing transport name to a BaseLink factory.

Mirrors hardware/plc_manager.py. To add a transport: implement BaseLink in a new
module and add one entry to _REGISTRY.
"""
from __future__ import annotations

from .base_link import BaseLink
from .mock_link import MockLink
from .serial_link import SerialLink
from .wifi_link import WifiLink

# name -> (factory(address) -> BaseLink, needs_address)
_REGISTRY = {
    "Mock (Demo)":  (lambda addr: MockLink(), False),
    "Serial (USB)": (lambda addr: SerialLink(addr), True),
    "Wi-Fi (TCP)":  (lambda addr: WifiLink(addr), True),
}


def get_link(kind: str, address: str = "") -> BaseLink:
    entry = _REGISTRY.get(kind)
    if entry is None:
        available = ", ".join(_REGISTRY)
        raise ValueError(f"Unknown link '{kind}'. Available: {available}")
    factory, _ = entry
    return factory(address)


def registered_link_types() -> list[str]:
    return list(_REGISTRY)


def needs_address(kind: str) -> bool:
    entry = _REGISTRY.get(kind)
    return bool(entry and entry[1])


def list_serial_ports() -> list[str]:
    """Available serial ports for the connection dropdown (empty if pyserial absent)."""
    try:
        from serial.tools import list_ports
    except ImportError:
        return []
    return [p.device for p in list_ports.comports()]
