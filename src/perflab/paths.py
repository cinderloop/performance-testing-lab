"""Repository locations and the pinned demo configuration."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


def _find_root() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "pyproject.toml").exists() and (parent / "demo" / "pin.json").exists():
            return parent
    raise RuntimeError("cannot locate the repository root (pyproject.toml + demo/pin.json)")


ROOT = _find_root()
DEMO_DIR = ROOT / "demo"
UPSTREAM_DIR = DEMO_DIR / ".upstream"
K6_DIR = ROOT / "k6"
RESULTS_DIR = ROOT / "results"
FLAGS_FILE = "src/flagd/demo.flagd.json"  # relative to UPSTREAM_DIR


@dataclass(frozen=True)
class Pin:
    repo: str
    tag: str
    commit: str
    compose_project: str
    compose_files: tuple[str, ...]
    network: str
    k6_image: str


def load_pin(path: Path | None = None) -> Pin:
    raw: dict[str, Any] = json.loads((path or DEMO_DIR / "pin.json").read_text())
    return Pin(
        repo=raw["demo"]["repo"],
        tag=raw["demo"]["tag"],
        commit=raw["demo"]["commit"],
        compose_project=raw["compose_project"],
        compose_files=tuple(raw["compose_files"]),
        network=raw["network"],
        k6_image=raw["k6_image"],
    )
