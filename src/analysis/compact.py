"""Compact per-sample file derived from k6's raw JSON output (ADR 0005, amended).

k6 `--out json` writes about ten metric lines per request (blocked, connecting, sending, waiting …),
roughly 140 bytes compressed per request. Analysis needs one line per request plus session-end and
dropped-session events. `samples.csv.gz` keeps exactly those, with the fields unchanged
(timestamps to the microsecond, durations as k6 wrote them). It's committed. The full raw file
stays local and is published as a GitHub Release asset, verified by the SHA-256 in
`raw_archive.json`.
"""

from __future__ import annotations

import csv
import gzip
import hashlib
import json
from pathlib import Path
from typing import Any

from analysis.raw import COLUMNS, KINDS, iter_points

COMPACT_FILE = "samples.csv.gz"


def write(raw_path: Path, out_path: Path) -> int:
    """Write the compact file; returns the number of rows."""
    rows = 0
    with gzip.open(out_path, "wt", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(COLUMNS)
        for p in iter_points(raw_path):
            kind = KINDS.get(p["metric"])
            if kind is None:
                continue
            data = p["data"]
            tags = data.get("tags", {})
            w.writerow([kind, data["time"], data["value"], *(tags.get(c, "") for c in COLUMNS[3:])])
            rows += 1
    return rows


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def archive_record(raw_path: Path) -> dict[str, Any]:
    return {
        "file": raw_path.name,
        "bytes": raw_path.stat().st_size,
        "sha256": sha256(raw_path),
        "committed": False,
        "where": "GitHub Release asset for the phase (see docs/scenarios.md); local copy kept",
    }


def finalize(run_dir: Path, raw_name: str = "k6-raw.json.gz") -> dict[str, Any]:
    """Write samples.csv.gz and raw_archive.json for a run directory."""
    raw = run_dir / raw_name
    rows = write(raw, run_dir / COMPACT_FILE)
    record = {**archive_record(raw), "compact_file": COMPACT_FILE, "compact_rows": rows}
    (run_dir / "raw_archive.json").write_text(json.dumps(record, indent=2) + "\n")
    return record
