"""Load k6 `--out json` raw output (one JSON object per line, optionally gzipped)."""

from __future__ import annotations

import csv
import gzip
import json
import re
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import IO, Any


@dataclass(frozen=True)
class Request:
    """One HTTP request. `start` is epoch seconds when it was sent (end time minus duration)."""

    start: float
    duration_ms: float
    ok: bool  # k6 `expected_response` tag: the request did what the user needed
    name: str
    group: str
    status: str
    error_code: str
    journey: str
    step: str


@dataclass
class RawRun:
    requests: list[Request]
    dropped_at: list[float]  # epoch seconds of each dropped_iterations sample
    iterations_at: list[float]  # epoch seconds when each session (iteration) ended
    first_sample: float | None


def _open(path: Path) -> IO[str]:
    if path.suffix == ".gz":
        return gzip.open(path, "rt")
    return path.open()


_FRACTION = re.compile(r"\.(\d{6})\d+")


def _epoch(value: str) -> float:
    """RFC 3339 with nanoseconds (k6 writes up to 9 digits; Python keeps microseconds)."""
    return datetime.fromisoformat(_FRACTION.sub(r".\1", value)).timestamp()


COLUMNS = (
    "kind",  # request | iteration | dropped
    "time",  # k6 sample time (RFC 3339, as written by k6): end of the request or session
    "value",  # request: duration in ms; iteration: 1; dropped: number of sessions dropped
    "expected_response",
    "name",
    "endpoint_group",
    "status",
    "error_code",
    "journey",
    "step",
    "scenario",
)
KINDS = {"http_req_duration": "request", "iterations": "iteration", "dropped_iterations": "dropped"}


def iter_compact(path: Path) -> Iterator[dict[str, Any]]:
    """Yield raw-JSON-shaped points from a compact file, so one loader serves both formats."""
    metric = {v: k for k, v in KINDS.items()}
    with gzip.open(path, "rt", newline="") as fh:
        for row in csv.DictReader(fh):
            tags = {c: row[c] for c in COLUMNS[3:] if row[c] != ""}
            yield {
                "type": "Point",
                "metric": metric[row["kind"]],
                "data": {"time": row["time"], "value": float(row["value"]), "tags": tags},
            }


def iter_points(path: Path) -> Iterator[dict[str, Any]]:
    with _open(path) as fh:
        for line in fh:
            obj: dict[str, Any] = json.loads(line)
            if obj.get("type") == "Point":
                yield obj


def load(path: Path) -> RawRun:
    """Load k6 raw JSON output or the compact samples.csv.gz (same result for both)."""
    if path.name.endswith(".csv.gz"):
        points: Iterator[dict[str, Any]] = iter_compact(path)
    else:
        points = iter_points(path)
    requests: list[Request] = []
    dropped: list[float] = []
    iterations: list[float] = []
    first: float | None = None
    for p in points:
        data = p["data"]
        t = _epoch(data["time"])
        first = t if first is None else min(first, t)
        metric = p["metric"]
        if metric == "http_req_duration":
            tags = data.get("tags", {})
            ms = float(data["value"])
            requests.append(
                Request(
                    start=t - ms / 1000,
                    duration_ms=ms,
                    ok=tags.get("expected_response") == "true",
                    name=tags.get("name", ""),
                    group=tags.get("endpoint_group", ""),
                    status=tags.get("status", ""),
                    error_code=tags.get("error_code", ""),
                    journey=tags.get("journey", ""),
                    step=tags.get("step", ""),
                )
            )
        elif metric == "dropped_iterations":
            dropped.extend([t] * int(data["value"]))
        elif metric == "iterations":
            iterations.append(t)
    requests.sort(key=lambda r: r.start)
    return RawRun(requests, sorted(dropped), sorted(iterations), first)
