"""Fixed time windows over a run, relative to the scenario clock (t0)."""

from __future__ import annotations

import math
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field

from analysis.raw import Request
from analysis.stats import percentile

WINDOW_S = 10.0  # matches the 10 s server-side metric resolution (docs/environment.md)


@dataclass
class Window:
    start_s: float  # seconds since t0
    ok_ms: list[float] = field(default_factory=list)
    failed: int = 0
    dropped: int = 0
    by_group_ok_ms: dict[str, list[float]] = field(default_factory=dict)

    @property
    def requests(self) -> int:
        return len(self.ok_ms) + self.failed

    @property
    def error_rate(self) -> float:
        return self.failed / self.requests if self.requests else math.nan

    def p95(self, group: str | None = None) -> float:
        values = self.ok_ms if group is None else self.by_group_ok_ms.get(group, [])
        return percentile(values, 95)


def windows(
    requests: Sequence[Request],
    t0: float,
    end_s: float,
    dropped_at: Sequence[float] = (),
    width_s: float = WINDOW_S,
) -> list[Window]:
    """Bucket requests by start time into [k*width, (k+1)*width) since t0, up to end_s."""
    n = max(1, math.ceil(end_s / width_s))
    out = [Window(start_s=k * width_s) for k in range(n)]

    def index(t: float) -> int | None:
        k = math.floor((t - t0) / width_s)
        return k if 0 <= k < n else None

    for r in requests:
        k = index(r.start)
        if k is None:
            continue
        w = out[k]
        if r.ok:
            w.ok_ms.append(r.duration_ms)
            w.by_group_ok_ms.setdefault(r.group, []).append(r.duration_ms)
        else:
            w.failed += 1
    for t in dropped_at:
        k = index(t)
        if k is not None:
            out[k].dropped += 1
    return out


def first_sustained(
    ws: Sequence[Window], predicate: Callable[[Window], bool], start: int = 0, run: int = 3
) -> int | None:
    """Index of the first window that starts `run` consecutive windows all matching predicate."""
    for i in range(start, len(ws) - run + 1):
        if all(predicate(ws[j]) for j in range(i, i + run)):
            return i
    return None
