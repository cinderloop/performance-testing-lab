"""Thin wrapper around `docker compose` for the pinned demo plus the lab overrides."""

from __future__ import annotations

import json
import subprocess
from typing import Any

from perflab.paths import DEMO_DIR, UPSTREAM_DIR, Pin, load_pin

# Services recreated by the reset protocol. Observability (grafana, jaeger, prometheus,
# opensearch, otel-collector) and opamp-server are kept so history survives between runs.
APP_TIER: tuple[str, ...] = (
    "accounting",
    "ad",
    "astronomy-db",
    "cart",
    "checkout",
    "currency",
    "email",
    "flagd",
    "flagd-ui",
    "fraud-detection",
    "frontend",
    "frontend-proxy",
    "image-provider",
    "kafka",
    "payment",
    "product-catalog",
    "quote",
    "recommendation",
    "shipping",
    "telemetry-docs",
    "valkey-cart",
)

# The two Go services ADR 0003 gates on.
GATED_GO_SERVICES: tuple[str, ...] = ("product-catalog", "checkout")


def base_args(pin: Pin | None = None) -> list[str]:
    """`docker compose` arguments selecting the pinned demo and every lab override."""
    pin = pin or load_pin()
    args = ["docker", "compose", "-p", pin.compose_project]
    args += ["--env-file", str(UPSTREAM_DIR / ".env"), "--env-file", str(DEMO_DIR / "demo.env")]
    for f in pin.compose_files:
        args += ["-f", str(UPSTREAM_DIR / f)]
    args += ["-f", str(DEMO_DIR / "compose.lab.yaml"), "-f", str(DEMO_DIR / "compose.images.yaml")]
    return args


def run(*args: str, check: bool = True, capture: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [*base_args(), *args],
        cwd=UPSTREAM_DIR,
        check=check,
        text=True,
        capture_output=capture,
    )


def resolved_config() -> dict[str, Any]:
    """The fully merged compose model (what `docker compose config` would apply)."""
    out = run("config", "--format", "json", capture=True).stdout
    config: dict[str, Any] = json.loads(out)
    return config
