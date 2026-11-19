"""Run-validity rules (ground rules 7 and 8). A run that breaks any rule is still recorded,
but flagged `valid: false` with every reason, and must not be used for comparison."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from perflab.conditions import Conditions, busy_processes

MIN_DOCKER_MEMORY_BYTES = 12_000_000_000  # spike §3: >= 12 GB for the Docker VM
AC_POWER = "AC Power"


@dataclass(frozen=True)
class RunFacts:
    reset_ran: bool
    reset_failures: list[str]
    loadgen_off: bool
    conditions_before: Conditions | None
    conditions_after: Conditions | None
    other_containers: list[str]
    git_dirty_files: list[str]
    digest_mismatches: list[str]
    docker_memory_bytes: int
    usage_report_disabled: bool
    display_sleep_prevented: bool
    events_during_run: list[str] = field(default_factory=list)


def condition_reasons(when: str, c: Conditions | None) -> list[str]:
    if c is None:
        return [f"{when}: laptop conditions were not captured"]
    reasons: list[str] = []
    if c.power_source != AC_POWER:
        reasons.append(f"{when}: not on mains power ({c.power_source or 'unknown'})")
    if c.low_power_mode is not False:
        reasons.append(f"{when}: Low Power Mode is {'on' if c.low_power_mode else 'unknown'}")
    if c.thermal_state != 0:
        state = "unknown" if c.thermal_state is None else str(c.thermal_state)
        reasons.append(f"{when}: thermal state not nominal ({state})")
    if c.heavy_apps_running:
        reasons.append(f"{when}: heavy applications running: {', '.join(c.heavy_apps_running)}")
    busy = busy_processes(c.top_processes)
    if busy:
        shown = ", ".join(f"{p.command} {p.cpu_percent:.0f}%" for p in busy)
        reasons.append(f"{when}: busy non-lab processes: {shown}")
    return reasons


def invalid_reasons(f: RunFacts) -> list[str]:
    reasons: list[str] = []
    if not f.reset_ran:
        reasons.append("reset protocol did not run")
    reasons += [f"reset check failed: {r}" for r in f.reset_failures]
    if not f.loadgen_off:
        reasons.append("demo load generator not confirmed off")
    reasons += condition_reasons("before", f.conditions_before)
    reasons += condition_reasons("after", f.conditions_after)
    if f.other_containers:
        reasons.append(f"other containers running: {', '.join(sorted(f.other_containers))}")
    if f.git_dirty_files:
        reasons.append(f"uncommitted changes in the repo ({len(f.git_dirty_files)} files)")
    reasons += [f"image digest mismatch: {m}" for m in f.digest_mismatches]
    if f.docker_memory_bytes < MIN_DOCKER_MEMORY_BYTES:
        gib = f.docker_memory_bytes / 2**30
        reasons.append(f"Docker VM memory {gib:.1f} GiB is below the 12 GB minimum")
    if not f.usage_report_disabled:
        reasons.append("k6 usage reporting was not disabled")
    reasons += [f"during the run: {e}" for e in f.events_during_run]
    if not f.display_sleep_prevented:
        reasons.append("display/system sleep was not prevented (caffeinate)")
    return reasons


def summarize(reasons: list[str]) -> dict[str, Any]:
    return {"valid": not reasons, "invalid_reasons": reasons}
