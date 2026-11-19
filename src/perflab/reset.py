"""Reset protocol (ground rule 7, docs/reset-protocol.md, ADR 0003 health gate).

Recreates the app tier with fresh anonymous volumes and pristine flags, waits for health, lets the
stack settle, then verifies the start state. Observability is kept so history survives.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any

from perflab import compose
from perflab.dockerapi import Docker, Sample, cores_between
from perflab.paths import FLAGS_FILE, UPSTREAM_DIR, load_pin

SHOP = "http://127.0.0.1:8080"
ENVOY_ADMIN = "http://127.0.0.1:10000"
PROMETHEUS = "http://127.0.0.1:9090"

SETTLE_SECONDS = 30
GATE_IDLE_CORES = 0.05  # ADR 0003: product-catalog / checkout above this at idle = GC thrashing
MAX_IDLE_FRONTEND_REQUESTS = 2  # collector http_check: about 1 per minute (spike §4)


@dataclass
class Check:
    name: str
    passed: bool
    observed: Any
    expected: str


@dataclass
class ResetReport:
    started_at: str
    finished_at: str = ""
    seconds_to_healthy: float = 0.0
    settle_seconds: int = SETTLE_SECONDS
    checks: list[Check] = field(default_factory=list)
    idle_cores: dict[str, float] = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        return bool(self.checks) and all(c.passed for c in self.checks)

    def failures(self) -> list[str]:
        return [
            f"{c.name}: observed {c.observed!r}, expected {c.expected}"
            for c in self.checks
            if not c.passed
        ]

    def to_json(self) -> dict[str, Any]:
        d = asdict(self)
        d["passed"] = self.passed
        return d


# --- pure evaluators (unit-tested) -----------------------------------------------------------


def check_orders(count: str) -> Check:
    return Check("orders_empty", count.strip() == "0", count.strip(), "0 rows in accounting.order")


def check_valkey(dbsize: str) -> Check:
    # The cart service writes one `cart` bookkeeping key on start (spike §8).
    n = int(dbsize.strip()) if dbsize.strip().isdigit() else -1
    return Check("carts_empty", 0 <= n <= 1, n, "<= 1 key")


def check_kafka(offsets: str) -> Check:
    found = re.findall(r"^orders:\d+:(\d+)$", offsets, re.MULTILINE)
    ok = bool(found) and all(o == "0" for o in found)
    return Check("kafka_orders_empty", ok, offsets.strip(), "every orders partition at offset 0")


def check_flags(live: dict[str, Any], pristine: dict[str, Any]) -> Check:
    want = {k: v["defaultVariant"] for k, v in pristine["flags"].items()}
    got = {k: v.get("defaultVariant") for k, v in live.get("flags", {}).items()}
    diff = {k: got.get(k) for k in want if got.get(k) != want[k]}
    extra = sorted(set(got) - set(want))
    return Check(
        "flags_pristine",
        not diff and not extra,
        {"differs": diff, "unexpected": extra},
        "every flag on its pinned defaultVariant",
    )


def check_loadgen(containers: list[dict[str, Any]], loadgen_http_status: int) -> list[Check]:
    names = [n.lstrip("/") for c in containers for n in c.get("Names", [])]
    present = [n for n in names if n == "load-generator"]
    return [
        Check("loadgen_no_container", not present, present, "no load-generator container"),
        Check("loadgen_route_dead", loadgen_http_status == 503, loadgen_http_status, "HTTP 503"),
    ]


def parse_envoy_counter(stats: str, name: str = "cluster.frontend.upstream_rq_total") -> int:
    m = re.search(rf"^{re.escape(name)}: (\d+)$", stats, re.MULTILINE)
    if not m:
        raise ValueError(f"{name} not found in Envoy stats")
    return int(m.group(1))


def check_idle_frontend(before: int, after: int) -> Check:
    delta = after - before
    return Check(
        "no_idle_traffic",
        delta <= MAX_IDLE_FRONTEND_REQUESTS,
        delta,
        f"<= {MAX_IDLE_FRONTEND_REQUESTS} frontend requests in {SETTLE_SECONDS}s "
        "(health checks only)",
    )


def check_gc_gate(idle_cores: dict[str, float]) -> list[Check]:
    return [
        Check(
            f"gc_gate_{svc}",
            svc in idle_cores and idle_cores[svc] <= GATE_IDLE_CORES,
            round(idle_cores.get(svc, float("nan")), 4),
            f"<= {GATE_IDLE_CORES} cores at idle (ADR 0003)",
        )
        for svc in compose.GATED_GO_SERVICES
    ]


def check_go_memory(used: dict[str, float], limit: dict[str, float]) -> list[Check]:
    checks = []
    for svc in compose.GATED_GO_SERVICES:
        u, lim = used.get(svc), limit.get(svc)
        checks.append(
            Check(
                f"go_memory_{svc}",
                u is not None and lim is not None and u < lim,
                {"used": u, "limit": lim},
                "go_memory_used_bytes < go_memory_limit_bytes",
            )
        )
    return checks


# --- I/O -----------------------------------------------------------------------------------


def _http(url: str, timeout: float = 10.0) -> tuple[int, str]:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return resp.status, resp.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode(errors="replace")


def _exec(container: str, *cmd: str) -> str:
    return subprocess.run(
        ["docker", "exec", container, *cmd], capture_output=True, text=True, timeout=60, check=False
    ).stdout


def _envoy_frontend_total() -> int:
    _, body = _http(f"{ENVOY_ADMIN}/stats?filter=^cluster.frontend.upstream_rq_total$")
    return parse_envoy_counter(body)


def _prom_by_service(metric: str) -> dict[str, float]:
    # go_memory_used_bytes is split by go_memory_type (stack / other), so sum per service.
    sel = f'{metric}{{job=~".*/(product-catalog|checkout)"}}'
    q = f"sum by (job) (last_over_time({sel}[20s]))"
    _, body = _http(f"{PROMETHEUS}/api/v1/query?query={urllib.parse.quote(q)}")
    out: dict[str, float] = {}
    for r in json.loads(body).get("data", {}).get("result", []):
        job = r["metric"].get("job", "")
        svc = job.rsplit("/", 1)[-1]
        out[svc] = float(r["value"][1])
    return out


def pristine_flags() -> dict[str, Any]:
    raw = subprocess.run(
        ["git", "-C", str(UPSTREAM_DIR), "show", f"HEAD:{FLAGS_FILE}"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    flags: dict[str, Any] = json.loads(raw)
    return flags


def upstream_state() -> Check:
    pin = load_pin()
    head = subprocess.run(
        ["git", "-C", str(UPSTREAM_DIR), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=False,
    ).stdout.strip()
    dirty = subprocess.run(
        ["git", "-C", str(UPSTREAM_DIR), "status", "--porcelain"],
        capture_output=True,
        text=True,
        check=False,
    ).stdout.strip()
    return Check(
        "upstream_pinned_and_clean",
        head == pin.commit and not dirty,
        {"head": head, "dirty": dirty.splitlines()},
        f"HEAD {pin.commit[:12]} with no local changes",
    )


def _sample_all(docker: Docker, names: list[str]) -> dict[str, Sample]:
    return {n: docker.sample(n) for n in names}


def reset(log: bool = True) -> ResetReport:
    def say(msg: str) -> None:
        if log:
            print(f"[reset] {msg}", file=sys.stderr, flush=True)

    report = ResetReport(started_at=datetime.now(UTC).isoformat())
    t0 = time.monotonic()

    say("1/6 restore pristine feature flags")
    subprocess.run(["git", "-C", str(UPSTREAM_DIR), "checkout", "--", FLAGS_FILE], check=True)
    report.checks.append(upstream_state())

    say("2/6 remove app-tier containers and their anonymous volumes")
    compose.run("rm", "--force", "--stop", "--volumes", *compose.APP_TIER, capture=True)

    say("3/6 recreate and wait for health")
    compose.run("up", "--detach", "--no-recreate", "--wait", "--wait-timeout", "300", capture=True)
    report.seconds_to_healthy = round(time.monotonic() - t0, 1)

    say(f"4/6 settle {SETTLE_SECONDS}s while measuring idle CPU and idle traffic")
    docker = Docker()
    running = sorted(
        n.lstrip("/")
        for c in docker.containers()
        if c.get("Labels", {}).get("com.docker.compose.project") == load_pin().compose_project
        for n in c.get("Names", [])
    )
    envoy_before = _envoy_frontend_total()
    first = _sample_all(docker, running)
    time.sleep(SETTLE_SECONDS)
    last = _sample_all(docker, running)
    envoy_after = _envoy_frontend_total()
    report.idle_cores = {n: round(cores_between(first[n], last[n]), 4) for n in running}

    say("5/6 verify start state")
    report.checks.append(
        check_orders(
            _exec(
                "astronomy-db",
                "psql",
                "-U",
                "postgres",
                "-d",
                "astronomy_db",
                "-Atc",
                'select count(*) from accounting."order"',
            )
        )
    )
    report.checks.append(check_valkey(_exec("valkey-cart", "valkey-cli", "dbsize")))
    report.checks.append(
        check_kafka(
            _exec(
                "kafka",
                "/opt/kafka/bin/kafka-get-offsets.sh",
                "--bootstrap-server",
                "kafka:9092",
                "--topic",
                "orders",
            )
        )
    )
    _, flags_body = _http(f"{SHOP}/feature/api/read")
    report.checks.append(check_flags(json.loads(flags_body), pristine_flags()))
    status, _ = _http(f"{SHOP}/loadgen/")
    report.checks.extend(check_loadgen(docker.containers(all_=True), status))
    report.checks.append(check_idle_frontend(envoy_before, envoy_after))

    say("6/6 health gate (ADR 0003)")
    report.checks.extend(check_gc_gate(report.idle_cores))
    report.checks.extend(
        check_go_memory(
            _prom_by_service("go_memory_used_bytes"), _prom_by_service("go_memory_limit_bytes")
        )
    )

    report.finished_at = datetime.now(UTC).isoformat()
    say(f"{'PASSED' if report.passed else 'FAILED'} in {round(time.monotonic() - t0)}s")
    for f in report.failures():
        say(f"  FAIL {f}")
    return report
