"""UI-only progress smoothing for yt-dlp's multiple media streams.

yt-dlp reports progress separately for video and audio. The second stream may
start at 0% after the first reaches 100%; this helper prevents a visual rewind.
Keep 100% reserved for the successful final file, never for a fragment.
"""
from __future__ import annotations

import math


def monotonic_download_percent(previous: float, incoming: object, status: object = "downloading") -> float:
    """Return a bounded, non-decreasing percentage for one download session.

    Caller resets previous=0 for each new download. "converting" shows >=99%;
    an ordinary stream never displays 100% before a completed output exists.
    """
    last = float(previous)
    if not math.isfinite(last):
        last = 0.0
    last = max(0.0, min(100.0, last))
    if status == "finished":
        return 100.0
    if status == "converting":
        return max(last, 99.0)
    try:
        value = float(incoming)
    except (ValueError, TypeError, OverflowError):
        return last
    if not math.isfinite(value):
        return last
    return max(last, min(98.0, max(0.0, value)))
