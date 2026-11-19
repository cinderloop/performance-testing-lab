"""Minimal Docker Engine API client over the local unix socket (stdlib only).

Used for container CPU/memory, which `docker stats --no-stream` snapshots get wrong for bursty
services (spike §3). CPU is computed from cumulative cgroup usage between two readings.
"""

from __future__ import annotations

import http.client
import json
import re
import socket
import subprocess
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from urllib.parse import quote


def socket_path() -> str:
    host = subprocess.run(
        ["docker", "context", "inspect", "--format", "{{.Endpoints.docker.Host}}"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if not host.startswith("unix://"):
        raise RuntimeError(f"unsupported Docker endpoint {host!r}; expected a local unix socket")
    return host.removeprefix("unix://")


class _UnixConnection(http.client.HTTPConnection):
    def __init__(self, path: str, timeout: float = 30.0) -> None:
        super().__init__("localhost", timeout=timeout)
        self._path = path

    def connect(self) -> None:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(self.timeout)
        sock.connect(self._path)
        self.sock = sock


@dataclass(frozen=True)
class Sample:
    """One cgroup reading for a container."""

    read: datetime
    cpu_ns: int
    mem_bytes: int  # usage minus inactive file cache, as `docker stats` reports it
    online_cpus: int


_FRACTION = re.compile(r"\.(\d{6})\d+")


def parse_time(value: str) -> datetime:
    """Parse Docker's RFC 3339 timestamps, which carry nanoseconds (Python keeps microseconds)."""
    return datetime.fromisoformat(_FRACTION.sub(r".\1", value))


def parse_sample(stats: dict[str, Any]) -> Sample:
    mem = stats.get("memory_stats") or {}
    usage = int(mem.get("usage") or 0)
    inactive = int((mem.get("stats") or {}).get("inactive_file") or 0)
    cpu = stats.get("cpu_stats") or {}
    return Sample(
        read=parse_time(stats["read"]),
        cpu_ns=int((cpu.get("cpu_usage") or {}).get("total_usage") or 0),
        mem_bytes=max(usage - inactive, 0),
        online_cpus=int(cpu.get("online_cpus") or 0),
    )


def cores_between(a: Sample, b: Sample) -> float:
    """Average CPU cores used between two readings of the same container."""
    wall_ns = (b.read - a.read).total_seconds() * 1e9
    if wall_ns <= 0:
        raise ValueError("samples must be in increasing time order")
    return (b.cpu_ns - a.cpu_ns) / wall_ns


class Docker:
    def __init__(self, path: str | None = None) -> None:
        self.path = path or socket_path()

    def _get(self, url: str, timeout: float = 30.0) -> Any:
        conn = _UnixConnection(self.path, timeout)
        try:
            conn.request("GET", url)
            resp = conn.getresponse()
            body = resp.read()
            if resp.status >= 400:
                raise RuntimeError(f"Docker API {url}: HTTP {resp.status} {body[:200]!r}")
            return json.loads(body)
        finally:
            conn.close()

    def containers(self, all_: bool = False) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = self._get(f"/containers/json?all={'1' if all_ else '0'}")
        return result

    def sample(self, container: str) -> Sample:
        stats = self._get(f"/containers/{quote(container)}/stats?stream=false&one-shot=true")
        return parse_sample(stats)

    def stream(self, container: str) -> Iterator[Sample]:
        """Yield about one reading per second until the container stops."""
        conn = _UnixConnection(self.path, timeout=3600)
        try:
            conn.request("GET", f"/containers/{quote(container)}/stats?stream=true")
            resp = conn.getresponse()
            if resp.status >= 400:
                raise RuntimeError(f"Docker stats stream: HTTP {resp.status}")
            while True:
                line = resp.readline()
                if not line:
                    return
                stats = json.loads(line)
                if not stats.get("read") or stats["read"].startswith("0001-"):
                    return  # container has stopped
                yield parse_sample(stats)
        finally:
            conn.close()
