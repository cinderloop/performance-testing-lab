"""macOS laptop conditions (ground rule 8, spike §13). No sudo: CPU frequency and temperature
need `powermetrics` (root), so they are recorded as not captured."""

from __future__ import annotations

import platform
import re
import subprocess
from dataclasses import asdict, dataclass, field
from typing import Any

# Processes that are part of the lab itself or of macOS's normal background, never counted as
# "other heavy applications". Matched as a prefix of the `top` command name.
ALLOWED_PROCESSES: tuple[str, ...] = (
    "com.docker",
    "com.apple.Virtua",  # Docker Desktop VM (Virtualization.framework); top truncates names
    "Docker",
    "docker",
    "vpnkit",
    "qemu",
    "krun",
    "virtualization",
    "Virtual Machine Service",
    "top",
    "python",
    "perflab",
    "uv",
    "kernel_task",
    "WindowServer",
    "launchd",
    "sysmond",
    "caffeinate",
)

# Applications that make a run invalid whenever they are running, busy or not (spike §13).
HEAVY_APPS: tuple[str, ...] = (
    "Google Chrome",
    "Transmission",
    "Firefox",
    "Slack",
    "zoom.us",
    "Microsoft Teams",
    "Spotify",
)

BUSY_PROCESS_CPU_PERCENT = 25.0  # a non-lab process above this, sampled over 2 s, is "heavy"


@dataclass(frozen=True)
class Proc:
    pid: int
    cpu_percent: float
    command: str


@dataclass
class Conditions:
    power_source: str | None
    low_power_mode: bool | None
    thermal_state: int | None  # ProcessInfo.thermalState: 0 nominal, 1 fair, 2 serious, 3 critical
    pmset_therm: str
    powermode: str | None
    load_average: list[float]
    top_processes: list[Proc] = field(default_factory=list)
    heavy_apps_running: list[str] = field(default_factory=list)
    not_captured: list[str] = field(
        default_factory=lambda: ["cpu_frequency", "cpu_temperature", "power_draw"]
    )

    def to_json(self) -> dict[str, Any]:
        return asdict(self)


def parse_power_source(pmset_batt: str) -> str | None:
    m = re.search(r"Now drawing from '([^']+)'", pmset_batt)
    return m.group(1) if m else None


def parse_powermode(pmset_g: str) -> str | None:
    m = re.search(r"^\s*powermode\s+(\d+)", pmset_g, re.MULTILINE)
    return m.group(1) if m else None


def parse_processinfo(out: str) -> tuple[bool | None, int | None]:
    lpm = re.search(r"lpm=(true|false)", out)
    thermal = re.search(r"thermal=(\d)", out)
    return (
        (lpm.group(1) == "true") if lpm else None,
        int(thermal.group(1)) if thermal else None,
    )


def parse_loadavg(out: str) -> list[float]:
    return [float(x) for x in re.findall(r"\d+\.\d+", out)[:3]]


def parse_top(out: str) -> list[Proc]:
    """Parse the *last* sample of `top -l 2 -stats pid,cpu,command` (the first has no CPU delta)."""
    blocks = re.split(r"^PID\s+%CPU\s+COMMAND\s*$", out, flags=re.MULTILINE)
    if len(blocks) < 2:
        return []
    procs: list[Proc] = []
    for line in blocks[-1].strip().splitlines():
        m = re.match(r"^\s*(\d+)\s+([\d.]+)\s+(.+?)\s*$", line)
        if m:
            procs.append(Proc(int(m.group(1)), float(m.group(2)), m.group(3)))
    return procs


def busy_processes(procs: list[Proc], extra_allowed: tuple[str, ...] = ()) -> list[Proc]:
    allowed = ALLOWED_PROCESSES + extra_allowed
    return [
        p
        for p in procs
        if p.cpu_percent >= BUSY_PROCESS_CPU_PERCENT
        and not any(p.command.startswith(a) for a in allowed)
    ]


def running_heavy_apps(ps_comm: str) -> list[str]:
    found = {app for app in HEAVY_APPS for line in ps_comm.splitlines() if f"/{app}" in line}
    return sorted(found)


def _sh(*cmd: str) -> str:
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=60, check=False).stdout
    except OSError, subprocess.TimeoutExpired:
        return ""


_SWIFT = (
    "import Foundation; let p = ProcessInfo.processInfo; "
    'print("lpm=\\(p.isLowPowerModeEnabled) thermal=\\(p.thermalState.rawValue)")'
)


def capture() -> Conditions:
    if platform.system() != "Darwin":
        raise RuntimeError("laptop-condition capture is implemented for macOS only")
    lpm, thermal = parse_processinfo(_sh("swift", "-e", _SWIFT))
    return Conditions(
        power_source=parse_power_source(_sh("pmset", "-g", "batt")),
        low_power_mode=lpm,
        thermal_state=thermal,
        pmset_therm=_sh("pmset", "-g", "therm").strip(),
        powermode=parse_powermode(_sh("pmset", "-g")),
        load_average=parse_loadavg(_sh("sysctl", "-n", "vm.loadavg")),
        top_processes=parse_top(
            _sh("top", "-l", "2", "-s", "2", "-o", "cpu", "-n", "15", "-stats", "pid,cpu,command")
        ),
        heavy_apps_running=running_heavy_apps(_sh("ps", "-Ao", "comm")),
    )


def host_details() -> dict[str, Any]:
    def sysctl(key: str) -> str:
        return _sh("sysctl", "-n", key).strip()

    return {
        "model": sysctl("hw.model"),
        "chip": sysctl("machdep.cpu.brand_string"),
        "cores": int(sysctl("hw.ncpu") or 0),
        "memory_bytes": int(sysctl("hw.memsize") or 0),
        "macos": _sh("sw_vers", "-productVersion").strip(),
        "macos_build": _sh("sw_vers", "-buildVersion").strip(),
    }
