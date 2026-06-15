"""Shared horological constants and engine defaults."""

# DS3231 dedicated 32 kHz output — the precision time base. Every beat timestamp
# coming off the ESP32 is expressed in ticks of this clock.
DS3231_TICKS_PER_SEC = 32768.0

# Standard balance train rates (beats per hour). A beat is one half-oscillation.
STANDARD_BPH = (18000, 19800, 21600, 25200, 28800, 36000)

# Default lift angle in degrees when a movement is unknown. ~52° is the common
# middle of the field (typical range 38–60°). Overridden per movement.
DEFAULT_LIFT_ANGLE = 52.0

# Sliding analysis window, in seconds, over which metrics are fitted.
DEFAULT_WINDOW_SECONDS = 6.0

# Minimum beats required in the window before metrics are considered valid.
MIN_BEATS_FOR_METRICS = 8

# Seconds in a day — rate is reported as s/day.
SECONDS_PER_DAY = 86400.0


def bph_to_nominal_interval(bph: float) -> float:
    """Nominal seconds between successive beats for a given BPH."""
    return 3600.0 / bph


def bph_to_osc_period(bph: float) -> float:
    """Full balance oscillation period (two beats) for a given BPH."""
    return 7200.0 / bph
