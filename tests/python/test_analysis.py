"""Analysis maths with hand-computed expected values."""

import gzip
import json
import math
import re
from pathlib import Path

import pytest

from analysis import criteria
from analysis.compact import finalize
from analysis.plan import Phase, Plan, parse
from analysis.raw import Request, load
from analysis.stats import describe, percentile
from analysis.windows import Window, first_sustained, windows

ROOT = Path(__file__).resolve().parents[2]
T0 = 1_000_000.0


def req(t: float, ms: float, ok: bool = True, group: str = "api", name: str = "api_x") -> Request:
    return Request(
        T0 + t, ms, ok, name, group, "200" if ok else "500", "" if ok else "1500", "", ""
    )


# --- percentile -----------------------------------------------------------------------------


def test_percentile_type7_by_hand() -> None:
    xs = [15.0, 20.0, 35.0, 40.0, 50.0]
    # n=5: h = 4*q/100
    assert percentile(xs, 0) == 15
    assert percentile(xs, 100) == 50
    assert percentile(xs, 50) == 35  # h=2 -> x[2]
    assert percentile(xs, 40) == 29  # h=1.6 -> 20 + 0.6*(35-20) = 29
    assert percentile(xs, 95) == pytest.approx(48)  # h=3.8 -> 40 + 0.8*10 = 48
    assert percentile([5.0, 1.0, 3.0], 25) == 2  # sorted [1,3,5], h=0.5 -> 1 + 0.5*2


def test_percentile_edges() -> None:
    assert math.isnan(percentile([], 95))
    assert percentile([7.0], 95) == 7
    with pytest.raises(ValueError, match="q must be"):
        percentile([1.0], 101)


def test_describe() -> None:
    d = describe([1.0, 2.0, 3.0, 4.0])
    assert d["count"] == 4
    assert d["median"] == 2.5  # h=1.5
    assert d["mean"] == 2.5
    assert describe([]) == {"count": 0}


# --- raw loader -------------------------------------------------------------------------------


def test_load_raw(tmp_path: Path) -> None:
    lines = [
        {"type": "Metric", "metric": "http_req_duration", "data": {}},
        {
            "type": "Point",
            "metric": "http_req_duration",
            "data": {
                "time": "2026-11-19T19:46:26.347763547Z",
                "value": 347.763,
                "tags": {
                    "expected_response": "true",
                    "name": "api_cart_get",
                    "endpoint_group": "api",
                },
            },
        },
        {
            "type": "Point",
            "metric": "http_req_duration",
            "data": {
                "time": "2026-11-19T19:46:27Z",
                "value": 10000.0,
                "tags": {"expected_response": "false", "status": "0", "error_code": "1050"},
            },
        },
        {
            "type": "Point",
            "metric": "dropped_iterations",
            "data": {"time": "2026-11-19T19:46:28Z", "value": 2},
        },
        {
            "type": "Point",
            "metric": "iterations",
            "data": {"time": "2026-11-19T19:46:29Z", "value": 1},
        },
    ]
    path = tmp_path / "k6-raw.json.gz"
    with gzip.open(path, "wt") as fh:
        fh.writelines(json.dumps(x) + "\n" for x in lines)
    raw = load(path)
    # Sorted by start time: the timed-out request started 10 s before the other one.
    second, first = raw.requests
    # start = end - duration: 26.347763 - 0.347763 = 26.000000 s past the minute
    assert first.start % 60 == pytest.approx(26.0, abs=1e-6)
    assert (first.ok, first.name, first.group) == (True, "api_cart_get", "api")
    assert (second.ok, second.status, second.error_code) == (False, "0", "1050")
    assert second.start % 60 == pytest.approx(17.0)  # timed out after 10 s
    assert len(raw.dropped_at) == 2
    assert len(raw.iterations_at) == 1


# --- windows ---------------------------------------------------------------------------------


def test_windows_bucket_by_start_time() -> None:
    rs = [
        req(0, 1),
        req(9.99, 2),
        req(10, 3),
        req(15, 4, ok=False),
        req(25, 5),
        req(-1, 9),
        req(31, 9),
    ]
    ws = windows(rs, T0, 30, dropped_at=[T0 + 12, T0 + 12.5])
    assert [w.start_s for w in ws] == [0, 10, 20]
    assert ws[0].ok_ms == [1, 2]
    assert (ws[1].ok_ms, ws[1].failed, ws[1].dropped) == ([3], 1, 2)
    assert ws[1].error_rate == 0.5
    assert ws[2].ok_ms == [5]  # -1 s and 31 s are outside [0, 30)


def test_first_sustained() -> None:
    flags = [False, True, True, False, True, True, True, False]
    ws = [Window(start_s=i * 10, failed=int(f)) for i, f in enumerate(flags)]
    assert first_sustained(ws, lambda w: w.failed == 1) == 4
    assert first_sustained(ws, lambda w: w.failed == 1, run=2) == 1
    assert first_sustained(ws, lambda w: w.failed == 1, start=5, run=3) is None


# --- plan ------------------------------------------------------------------------------------

PLAN_JSON = {
    "plan": {
        "scenario": "stress",
        "totalS": 100,
        "phases": [
            {"name": "baseline", "startS": 0, "endS": 40, "startPerMin": 60, "targetPerMin": 60},
            {"name": "peak", "startS": 40, "endS": 60, "startPerMin": 60, "targetPerMin": 600},
            {"name": "drop", "startS": 60, "endS": 70, "startPerMin": 600, "targetPerMin": 60},
            {"name": "recovery", "startS": 70, "endS": 100, "startPerMin": 60, "targetPerMin": 60},
        ],
    },
    "t0Ms": T0 * 1000,
}


def test_plan_rate_interpolation() -> None:
    p = parse(PLAN_JSON)
    assert p is not None
    assert p.t0 == T0
    assert p.rate_at(10) == 60
    assert p.rate_at(50) == 330  # halfway from 60 to 600
    assert p.rate_at(65) == 330  # halfway back down
    assert p.rate_at(1000) == 60
    assert parse({"plan": None}) is None


# --- recovery --------------------------------------------------------------------------------


def stress_requests(recovered_from_s: float) -> list[Request]:
    """30 ok requests per 10 s window. Baseline 10 ms; slow (500 ms) from 40 s until
    `recovered_from_s`, then 10 ms again."""
    out = []
    for w in range(10):
        for i in range(30):
            t = w * 10 + i * 0.3
            out.append(req(t, 500 if 40 <= t < recovered_from_s else 10))
    return out


def test_recovery_time_by_hand() -> None:
    p = parse(PLAN_JSON)
    assert p is not None
    rs = stress_requests(recovered_from_s=80)
    result = criteria.recovery(rs, windows(rs, T0, p.total_s), p)
    # Baseline = second half of "baseline" (20-40 s): all 10 ms -> p95 10, limit max(15, 35) = 35.
    assert result["baseline"]["p95_ms"] == 10
    assert result["limits"]["p95_ms"] == 35
    # Drop starts at 60 s; windows 80, 90 ... are fine, and 80+90+... gives 3 in a row only if
    # the plan has 3 windows from 80 s: 80, 90 exist within 100 s -> only two. Not recovered.
    assert result["recovered"] is False


def test_recovery_found() -> None:
    p = parse(PLAN_JSON)
    assert p is not None
    rs = stress_requests(recovered_from_s=70)
    result = criteria.recovery(rs, windows(rs, T0, p.total_s), p)
    # Windows 70, 80, 90 are back at 10 ms -> recovered at 70 s, i.e. 10 s after the drop at 60 s.
    assert result["recovered"] is True
    assert result["time_to_recover_s"] == 10


def test_recovery_not_applicable_without_phases() -> None:
    p = Plan("load", (Phase("steady", 0, 10, 1, 1),), 10, T0)
    assert criteria.recovery([], [], p) == {"applicable": False}


# --- breakpoint ------------------------------------------------------------------------------


def test_breakpoint_by_hand() -> None:
    ramp = Plan("breakpoint", (Phase("ramp", 0, 100, 0, 1000),), 100, T0)  # +10/min per second
    rs = []
    for w in range(10):
        for i in range(40):
            t = w * 10 + i * 0.25
            # api p95 breaks its 500 ms limit from 60 s on
            rs.append(req(t, 900 if t >= 60 else 20))
    result = criteria.breakpoint(windows(rs, T0, 100), ramp)
    assert result["found"] is True
    assert result["first_failing_window_s"] == 60
    assert result["last_good_window_s"] == 50
    assert result["breakpoint_per_min"] == 500  # planned rate at 50 s
    assert result["rate_at_failure_per_min"] == 600


def test_breakpoint_error_rate_and_not_found() -> None:
    ramp = Plan("breakpoint", (Phase("ramp", 0, 50, 0, 500),), 50, T0)
    healthy = [req(t * 0.25, 20) for t in range(200)]
    assert criteria.breakpoint(windows(healthy, T0, 50), ramp)["found"] is False
    # 1 failure in 40 requests = 2.5% >= 1% in every window from 20 s
    rs = [req(t * 0.25, 20, ok=not (t * 0.25 >= 20 and t % 40 == 0)) for t in range(200)]
    assert criteria.breakpoint(windows(rs, T0, 50), ramp)["first_failing_window_s"] == 20


def test_window_threshold_needs_enough_samples() -> None:
    w = Window(start_s=0, ok_ms=[900.0] * 5, by_group_ok_ms={"api": [900.0] * 5})
    assert criteria.window_breaks_thresholds(w) is False  # 5 < MIN_OK_PER_WINDOW


# --- soak ------------------------------------------------------------------------------------


def test_soak_trend() -> None:
    p = Plan("soak", (Phase("steady", 0, 1800, 60, 60),), 1800, T0)
    rs = [req(t, 10) for t in range(0, 600)] + [req(t, 13) for t in range(1200, 1800)]
    s = criteria.soak_trend(rs, p)
    assert s["p95_ratio_last_over_first"] == 1.3
    assert s["degraded"] is True
    short = Plan("soak", (Phase("steady", 0, 900, 60, 60),), 900, T0)
    assert criteria.soak_trend(rs, short) == {"applicable": False}


# --- keep Python criteria in sync with the k6 thresholds -----------------------------------------


def test_thresholds_match_k6() -> None:
    ts = (ROOT / "k6/lib/thresholds.ts").read_text()
    assert f'http_req_failed: ["rate<{criteria.ERROR_RATE_LIMIT}"]' in ts
    found = dict(
        re.findall(r"endpoint_group:(\w+),expected_response:true}\": \[\"p\(95\)<(\d+)\"\]", ts)
    )
    assert {k: float(v) for k, v in found.items()} == criteria.GROUP_P95_LIMIT_MS


# --- compact format ------------------------------------------------------------------------


def test_compact_round_trip_gives_identical_analysis(tmp_path: Path) -> None:
    points = []
    for i in range(50):
        points.append(
            {
                "type": "Point",
                "metric": "http_req_duration",
                "data": {
                    "time": f"2026-11-19T19:46:{i:02d}.123456789Z",
                    "value": 1.5 + i,
                    "tags": {
                        "expected_response": "true" if i % 7 else "false",
                        "name": "api_x",
                        "endpoint_group": "api",
                        "status": "200" if i % 7 else "500",
                        "journey": "buy",
                        "step": "checkout",
                    },
                },
            }
        )
        points.append(
            {
                "type": "Point",
                "metric": "http_req_waiting",
                "data": {"time": "2026-11-19T19:46:00Z", "value": 1},
            }
        )
    points.append(
        {
            "type": "Point",
            "metric": "dropped_iterations",
            "data": {"time": "2026-11-19T19:47:00Z", "value": 3},
        }
    )
    points.append(
        {
            "type": "Point",
            "metric": "iterations",
            "data": {"time": "2026-11-19T19:47:01Z", "value": 1},
        }
    )
    raw_path = tmp_path / "k6-raw.json.gz"
    with gzip.open(raw_path, "wt") as fh:
        fh.writelines(json.dumps(p) + "\n" for p in points)
    record = finalize(tmp_path)
    assert record["compact_rows"] == 52  # 50 requests + 1 dropped + 1 iteration, no other metrics
    assert len(record["sha256"]) == 64
    full, small = load(raw_path), load(tmp_path / "samples.csv.gz")
    # Everything analysis reads is identical. (`first_sample` differs only because the compact
    # file drops other metrics' timestamps; analysis takes t0 from setup(), not from it.)
    assert full.requests == small.requests
    assert (full.dropped_at, full.iterations_at) == (small.dropped_at, small.iterations_at)
