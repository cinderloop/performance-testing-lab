"""Port policy check (ground rule 4): every published port must bind to 127.0.0.1."""

from __future__ import annotations

from typing import Any

LOOPBACK = "127.0.0.1"


def port_violations(config: dict[str, Any]) -> list[str]:
    """Return one message per published port not bound to loopback, for a resolved compose model."""
    problems: list[str] = []
    for name, service in sorted((config.get("services") or {}).items()):
        for port in service.get("ports") or []:
            host_ip = port.get("host_ip")
            if host_ip != LOOPBACK:
                shown = host_ip or "0.0.0.0 (all interfaces)"
                problems.append(
                    f"{name}: container port {port.get('target')} published on {shown}, "
                    f"host port {port.get('published') or 'random'}"
                )
    return problems


def published_ports(config: dict[str, Any]) -> list[str]:
    """Human-readable list of what is published, for the manifest and docs."""
    found: list[str] = []
    for name, service in sorted((config.get("services") or {}).items()):
        for port in service.get("ports") or []:
            found.append(
                f"{port.get('host_ip')}:{port.get('published')} -> {name}:{port.get('target')}"
            )
    return found
