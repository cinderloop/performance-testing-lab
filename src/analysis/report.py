"""Per-run report from raw data: successes and failures separately, per endpoint, group and phase,
plus the scenario's computed pass criteria. Writes `report.json` next to the raw data."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from analysis import criteria
from analysis import plan as plan_mod
from analysis.raw import Request, load
from analysis.stats import describe
from analysis.windows import WINDOW_S, windows


def _split(rs: Sequence[Request]) -> dict[str, Any]:
    ok = [r.duration_ms for r in rs if r.ok]
    failed = [r for r in rs if not r.ok]
    return {
        "requests": len(rs),
        "error_rate": round(len(failed) / len(rs), 5) if rs else None,
        "success_ms": describe(ok),
        "failure_ms": describe([r.duration_ms for r in failed]),
        "failures_by_status_and_error": dict(
            Counter(f"{r.status}/{r.error_code or '-'}" for r in failed).most_common()
        ),
    }


def _by(rs: Sequence[Request], key: str) -> dict[str, Any]:
    groups: dict[str, list[Request]] = defaultdict(list)
    for r in rs:
        groups[getattr(r, key)].append(r)
    return {k: _split(v) for k, v in sorted(groups.items())}


def build(run_dir: Path) -> dict[str, Any]:
    raw = load(run_dir / "k6-raw.json.gz")
    plan = plan_mod.load(run_dir / "scenario-plan.json")
    rs = raw.requests
    report: dict[str, Any] = {
        "run_dir": run_dir.name,
        "source": "k6-raw.json.gz (every request); percentiles: linear interpolation (type 7)",
        "warmup_excluded": None,
        "overall": _split(rs),
        "by_group": _by(rs, "group"),
        "by_endpoint": _by(rs, "name"),
        "by_journey": _by(rs, "journey"),
        "sessions_completed": len(raw.iterations_at),
        "dropped_iterations": len(raw.dropped_at),
    }
    if plan is not None and plan.t0 is not None:
        ws = windows(rs, plan.t0, plan.total_s + 40, raw.dropped_at)  # + gracefulStop and slack
        report["plan"] = {"scenario": plan.scenario, "t0": plan.t0, "window_s": WINDOW_S}
        report["by_phase"] = {
            p.name: {
                "start_s": p.start_s,
                "end_s": p.end_s,
                "planned_per_min": [p.start_per_min, p.target_per_min],
                **_split([r for r in rs if p.start_s <= r.start - plan.t0 < p.end_s]),
                "dropped_iterations": sum(
                    1 for t in raw.dropped_at if p.start_s <= t - plan.t0 < p.end_s
                ),
            }
            for p in plan.phases
        }
        report["windows"] = criteria.window_series(ws)
        report["recovery"] = criteria.recovery(rs, ws, plan)
        report["soak_trend"] = criteria.soak_trend(rs, plan)
        if plan.scenario == "breakpoint":
            report["breakpoint"] = criteria.breakpoint(ws, plan)
    return report


def text(report: dict[str, Any]) -> str:
    lines = [f"report {report['run_dir']}"]

    def row(label: str, s: dict[str, Any]) -> str:
        ok = s["success_ms"]
        med, p95 = ok.get("median", "-"), ok.get("p95", "-")
        err = s["error_rate"] if s["error_rate"] is not None else 0
        fails = s["failures_by_status_and_error"]
        return f"  {label:24} n={s['requests']:<7} err={err:.2%}  ok med={med} p95={p95} ms" + (
            f"  failures {fails}" if fails else ""
        )

    lines.append(row("ALL", report["overall"]))
    lines += [row(f"group {k}", v) for k, v in report["by_group"].items()]
    lines += [row(k, v) for k, v in report["by_endpoint"].items()]
    for p, v in report.get("by_phase", {}).items():
        lines.append(row(f"phase {p}", v) + f"  dropped={v['dropped_iterations']}")
    rec = report.get("recovery", {})
    if rec.get("applicable"):
        lines.append(
            f"  recovery: {'recovered' if rec['recovered'] else 'NOT recovered'}"
            + (f" in {rec['time_to_recover_s']:.0f} s" if rec["recovered"] else "")
            + f" (baseline p95 {rec['baseline']['p95_ms']} ms, limit {rec['limits']['p95_ms']} ms)"
        )
    bp = report.get("breakpoint")
    if bp:
        lines.append(
            f"  breakpoint: {bp['breakpoint_per_min']} sessions/min (thresholds failed from "
            f"{bp['first_failing_window_s']:.0f} s)"
            if bp["found"]
            else f"  breakpoint: not reached ({bp['note']})"
        )
    soak = report.get("soak_trend", {})
    if soak.get("applicable"):
        lines.append(
            f"  soak: p95 last/first 10 min = {soak['p95_ratio_last_over_first']}"
            f" ({'DEGRADED' if soak['degraded'] else 'stable'})"
        )
    return "\n".join(lines) + "\n"


def write(run_dir: Path) -> dict[str, Any]:
    report = build(run_dir)
    (run_dir / "report.json").write_text(json.dumps(report, indent=1) + "\n")
    return report
