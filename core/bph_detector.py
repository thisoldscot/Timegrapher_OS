"""Beat-rate (BPH) detection from raw beat intervals."""
from __future__ import annotations

import statistics

from .constants import STANDARD_BPH


def detect_bph(onsets_s, snap: bool = True):
    """Estimate BPH from a sequence of beat onset times (seconds).

    Uses the median inter-onset interval (robust to missed/extra detections),
    then optionally snaps to the nearest standard train rate.

    Returns (bph, raw_bph, snapped) or None if there is too little data.
    """
    if len(onsets_s) < 4:
        return None

    intervals = [b - a for a, b in zip(onsets_s, onsets_s[1:]) if b > a]
    if not intervals:
        return None

    median_interval = statistics.median(intervals)
    if median_interval <= 0:
        return None

    raw_bph = 3600.0 / median_interval
    if not snap:
        return (raw_bph, raw_bph, False)

    nearest = min(STANDARD_BPH, key=lambda s: abs(s - raw_bph))
    # Only snap when we are within ~6% of a standard rate; otherwise the
    # detection is unreliable and we hand back the raw estimate untouched.
    snapped = abs(nearest - raw_bph) / nearest <= 0.06
    return (float(nearest) if snapped else raw_bph, raw_bph, snapped)
