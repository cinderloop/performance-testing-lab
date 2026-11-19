"""Descriptive statistics with one, stated percentile definition."""

from __future__ import annotations

import math
from collections.abc import Sequence
from typing import Any


def percentile(values: Sequence[float], q: float) -> float:
    """Linear interpolation between closest ranks (Hyndman & Fan type 7, numpy's default).

    For sorted x of length n, the position is h = (n - 1) * q / 100 and the result is
    x[floor(h)] + (h - floor(h)) * (x[floor(h) + 1] - x[floor(h)]). NaN for no data.
    """
    if not 0 <= q <= 100:
        raise ValueError("q must be within [0, 100]")
    if not values:
        return math.nan
    xs = sorted(values)
    h = (len(xs) - 1) * q / 100
    lo = math.floor(h)
    hi = min(lo + 1, len(xs) - 1)
    return xs[lo] + (h - lo) * (xs[hi] - xs[lo])


def describe(values: Sequence[float]) -> dict[str, Any]:
    """Count and the latency statistics every report uses (ms)."""
    if not values:
        return {"count": 0}
    return {
        "count": len(values),
        "min": round(min(values), 3),
        "median": round(percentile(values, 50), 3),
        "p90": round(percentile(values, 90), 3),
        "p95": round(percentile(values, 95), 3),
        "p99": round(percentile(values, 99), 3),
        "max": round(max(values), 3),
        "mean": round(sum(values) / len(values), 3),
    }
