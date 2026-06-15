"""Hardware link layer — transport-agnostic access to the ESP32.

Mirrors the BasePLC + plc_manager registry pattern from PLC-SQL-Bridge. Every
transport (serial, Wi-Fi, BLE, mock) implements BaseLink and is registered in
link_manager, so the UI picks one from a dropdown without knowing the details.
"""
