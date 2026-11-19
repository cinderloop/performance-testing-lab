"""Pass criteria computed from raw data (docs/thresholds.md). All PROVISIONAL until Phase 4.8.

- Recovery (stress, spike): time from the start of the load drop until three consecutive 10 s
  windows are back within tolerance of the baseline.
- Breakpoint: the highest planned arrival rate before the provisional thresholds fail for three
  consecutive 10 s windows.
- Soak trend: success p95 in the last 10 minutes of the steady phase vs the first 10 minutes.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from typing import Any

from analysis.plan import Plan
from analysis.raw import Request
from analysis.stats import percentile
from analysis.windows import WINDOW_S, Window, first_sustained

# Mirror of k6/lib/thresholds.ts (a unit test keeps them in sync).
ERROR_RATE_LIMIT = 0.01
GROUP_P95_LIMIT_MS: dict[str, float] = {"page": 1000, "api": 500, "flags": 500}

# Recovery tolerance (ASSUMPTION, provisional).
RECOVERY_P95_FACTOR = 1.5
RECOVERY_P95_SLACK_MS = 25.0
RECOVERY_ERROR_SLACK = 0.01
MIN_OK_PER_WINDOW = 20
SUSTAINED_WINDOWS = 3

# Soak trend (ASSUMPTION, provisional).
SOAK_EDGE_S = 600.0
SOAK_DEGRADED_FACTOR = 1.2


def window_breaks_thresholds(w: Window) -> bool:
    """True when a window violates the provisional error-rate or per-group p95 thresholds."""
    if w.requests == 0:
        return False
    if w.error_rate >= ERROR_RATE_LIMIT:
        return True
    return any(
        len(w.by_group_ok_ms.get(g, [])) >= MIN_OK_PER_WINDOW and w.p95(g) >= limit
        for g, limit in GROUP_P95_LIMIT_MS.items()
    )


def breakpoint(ws: Sequence[Window], plan: Plan) -> dict[str, Any]:
    first_bad = first_sustained(ws, window_breaks_thresholds, run=SUSTAINED_WINDOWS)
    if first_bad is None:
        return {"found": False, "note": "thresholds held for the whole ramp"}
    last_good = max(first_bad - 1, 0)
    t = ws[last_good].start_s
    return {
        "found": True,
        "first_failing_window_s": ws[first_bad].start_s,
        "last_good_window_s": t,
        "breakpoint_per_min": math.floor(plan.rate_at(t)),
        "rate_at_failure_per_min": math.floor(plan.rate_at(ws[first_bad].start_s)),
        "failing_window": _window_json(ws[first_bad]),
        "rule": (
            f"{SUSTAINED_WINDOWS} consecutive {WINDOW_S:.0f} s windows with error rate >= "
            f"{ERROR_RATE_LIMIT:.0%} or success p95 above a group limit {GROUP_P95_LIMIT_MS}"
        ),
    }


def baseline_stats(
    requests: Sequence[Request], t0: float, start_s: float, end_s: float
) -> dict[str, float]:
    """Success p95 and error rate over [start_s, end_s) of the run."""
    sel = [r for r in requests if start_s <= r.start - t0 < end_s]
    ok = [r.duration_ms for r in sel if r.ok]
    return {
        "p95_ms": percentile(ok, 95),
        "error_rate": (len(sel) - len(ok)) / len(sel) if sel else math.nan,
        "requests": len(sel),
    }


def recovery(requests: Sequence[Request], ws: Sequence[Window], plan: Plan) -> dict[str, Any]:
    base, drop, rec = plan.phase("baseline"), plan.phase("drop"), plan.phase("recovery")
    if base is None or drop is None or rec is None or plan.t0 is None:
        return {"applicable": False}
    # Second half of the baseline phase: after ramp-up effects have settled.
    b = baseline_stats(requests, plan.t0, (base.start_s + base.end_s) / 2, base.end_s)
    p95_limit = max(b["p95_ms"] * RECOVERY_P95_FACTOR, b["p95_ms"] + RECOVERY_P95_SLACK_MS)
    err_limit = b["error_rate"] + RECOVERY_ERROR_SLACK

    def recovered(w: Window) -> bool:
        return (
            len(w.ok_ms) >= MIN_OK_PER_WINDOW and w.p95() <= p95_limit and w.error_rate <= err_limit
        )

    start_index = math.ceil(drop.start_s / WINDOW_S)
    i = first_sustained(ws, recovered, start=start_index, run=SUSTAINED_WINDOWS)
    result: dict[str, Any] = {
        "applicable": True,
        "baseline": {k: _r(v) for k, v in b.items()},
        "limits": {"p95_ms": _r(p95_limit), "error_rate": _r(err_limit)},
        "load_drop_at_s": drop.start_s,
        "recovery_period_end_s": rec.end_s,
    }
    if i is None or ws[i].start_s >= rec.end_s:
        result.update(recovered=False, time_to_recover_s=None)
    else:
        result.update(recovered=True, time_to_recover_s=ws[i].start_s - drop.start_s)
    return result


def soak_trend(requests: Sequence[Request], plan: Plan) -> dict[str, Any]:
    steady = plan.phase("steady")
    if steady is None or plan.t0 is None or steady.end_s - steady.start_s < 3 * SOAK_EDGE_S:
        return {"applicable": False}
    first = baseline_stats(requests, plan.t0, steady.start_s, steady.start_s + SOAK_EDGE_S)
    last = baseline_stats(requests, plan.t0, steady.end_s - SOAK_EDGE_S, steady.end_s)
    ratio = last["p95_ms"] / first["p95_ms"] if first["p95_ms"] else math.nan
    return {
        "applicable": True,
        "first_10_min": {k: _r(v) for k, v in first.items()},
        "last_10_min": {k: _r(v) for k, v in last.items()},
        "p95_ratio_last_over_first": _r(ratio),
        "degraded": ratio > SOAK_DEGRADED_FACTOR,
        "rule": f"degraded if last-10-min success p95 > {SOAK_DEGRADED_FACTOR} x first-10-min",
    }


def _r(v: float, digits: int = 4) -> float | None:
    return None if math.isnan(v) else round(v, digits)


def _window_json(w: Window) -> dict[str, Any]:
    return {
        "start_s": w.start_s,
        "requests": w.requests,
        "error_rate": _r(w.error_rate),
        "p95_ms": _r(w.p95(), 2),
        "p95_by_group_ms": {
            g: _r(percentile(v, 95), 2) for g, v in sorted(w.by_group_ok_ms.items())
        },
        "dropped_iterations": w.dropped,
    }


def window_series(ws: Sequence[Window]) -> list[dict[str, Any]]:
    return [_window_json(w) for w in ws]
