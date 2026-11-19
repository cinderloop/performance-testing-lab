"""The scenario plan written by the k6 scripts (`scenario-plan.json`)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Phase:
    name: str
    start_s: float
    end_s: float
    start_per_min: float
    target_per_min: float


@dataclass(frozen=True)
class Plan:
    scenario: str
    phases: tuple[Phase, ...]
    total_s: float
    t0: float | None  # epoch seconds; None if setup() didn't record it

    def phase(self, name: str) -> Phase | None:
        return next((p for p in self.phases if p.name == name), None)

    def rate_at(self, t_s: float) -> float:
        """Planned arrival rate (sessions/min) at t_s seconds, interpolating each phase linearly."""
        for p in self.phases:
            if p.start_s <= t_s < p.end_s:
                f = (t_s - p.start_s) / (p.end_s - p.start_s)
                return p.start_per_min + f * (p.target_per_min - p.start_per_min)
        return self.phases[-1].target_per_min if self.phases else 0.0


def parse(raw: dict[str, Any]) -> Plan | None:
    p = raw.get("plan")
    if not p:
        return None
    phases = tuple(
        Phase(ph["name"], ph["startS"], ph["endS"], ph["startPerMin"], ph["targetPerMin"])
        for ph in p["phases"]
    )
    t0 = raw.get("t0Ms")
    return Plan(p["scenario"], phases, p["totalS"], t0 / 1000 if t0 else None)


def load(path: Path) -> Plan | None:
    return parse(json.loads(path.read_text())) if path.exists() else None
