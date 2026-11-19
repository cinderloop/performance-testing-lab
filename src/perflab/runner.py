"""Runner: reset -> capture conditions -> run k6 in a container -> manifest (ADR 0001, 0005).

Writes results/<run-id>/:
  manifest.json      everything needed to judge and reproduce the run
  k6-raw.json.gz     one line per sample (k6 `--out json`), the source of truth for analysis
  k6-summary.json    k6's end-of-test summary data (convenience only)
  k6-stdout.log      k6 console output
  k6-resources.csv   the k6 container's own CPU and memory, about once per second
  reset.json         the reset protocol report
  scenario-plan.json the scenario's phases and start time (written by the k6 script)
  report.json        per-endpoint/group/phase stats and computed pass criteria (analysis.report)
"""

from __future__ import annotations

import csv
import json
import os
import platform
import secrets
import subprocess
import sys
import threading
import urllib.error
import urllib.request
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from analysis import report
from perflab import compose, conditions
from perflab.dockerapi import Docker, Sample, cores_between
from perflab.paths import K6_DIR, RESULTS_DIR, ROOT, load_pin
from perflab.reset import SHOP, check_loadgen, reset
from perflab.validity import RunFacts, invalid_reasons, summarize

TARGET_URL = "http://frontend-proxy:8080"  # in-network address (ADR 0001)
DEFAULT_TIMEOUT_MS = 10_000  # mirrors k6/lib/config.ts (ADR 0008)
RAW_FILE = "k6-raw.json.gz"


@dataclass
class RunOptions:
    scenario: str
    experiment: str | None = None
    skip_reset: bool = False
    require_valid: bool = False
    k6_args: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)


def make_run_id(scenario: str, now: datetime | None = None) -> str:
    now = now or datetime.now(UTC)
    stem = Path(scenario).stem
    return f"{now.strftime('%Y%m%dT%H%M%SZ')}-{stem}-{secrets.token_hex(2)}"


def script_env(run_id: str, extra: dict[str, str]) -> dict[str, str]:
    """Variables for the k6 script (`__ENV`), passed with k6's own `-e` flag."""
    env = {
        "BASE_URL": TARGET_URL,
        "RUN_ID": run_id,
        "RESULTS_DIR": "/results",
        "TIMEOUT_MS": str(DEFAULT_TIMEOUT_MS),
    }
    env.update(extra)
    return env


def k6_command(
    *,
    image: str,
    network: str,
    container: str,
    scenario: str,
    results: Path,
    env: dict[str, str],
    k6_args: list[str],
) -> list[str]:
    """The exact `docker create` command for the k6 container (recorded in the manifest).

    Usage reporting is disabled twice (env var and flag) and can't be overridden (spike §15).
    """
    cmd = [
        "docker",
        "create",
        "--name",
        container,
        "--network",
        network,
        "-e",
        "K6_NO_USAGE_REPORT=true",
        "-v",
        f"{K6_DIR}:/k6:ro",
        "-v",
        f"{results}:/results",
        image,
        "run",
        "--quiet",
        "--no-usage-report",
        "--out",
        f"json=/results/{RAW_FILE}",
    ]
    for k, v in sorted(env.items()):
        cmd += ["-e", f"{k}={v}"]
    return [*cmd, *k6_args, f"/k6/{scenario}"]


def _out(*cmd: str) -> str:
    return subprocess.run(cmd, capture_output=True, text=True, check=False).stdout.strip()


def code_changes(porcelain: str) -> list[str]:
    """Uncommitted changes that matter for reproducibility. Run outputs under results/ don't."""
    return [
        line
        for line in porcelain.splitlines()
        if line and not line[3:].strip('"').startswith("results/")
    ]


def git_state() -> tuple[str, list[str]]:
    commit = _out("git", "-C", str(ROOT), "rev-parse", "HEAD")
    porcelain = _out("git", "-C", str(ROOT), "status", "--porcelain", "--untracked-files=all")
    return commit, code_changes(porcelain)


def docker_facts() -> dict[str, Any]:
    info = json.loads(_out("docker", "info", "--format", "{{json .}}") or "{}")
    return {
        "desktop": _out("docker", "version", "--format", "{{.Server.Platform.Name}}"),
        "engine": info.get("ServerVersion"),
        "compose": _out("docker", "compose", "version", "--short"),
        "vm_cpus": info.get("NCPU"),
        "vm_memory_bytes": info.get("MemTotal"),
        "kernel": info.get("KernelVersion"),
    }


def images_and_mismatches(
    docker: Docker, config: dict[str, Any]
) -> tuple[dict[str, Any], list[str]]:
    project = load_pin().compose_project
    images: dict[str, Any] = {}
    mismatches: list[str] = []
    for c in docker.containers():
        labels = c.get("Labels", {})
        if labels.get("com.docker.compose.project") != project:
            continue
        svc = labels.get("com.docker.compose.service", "?")
        expected_ref = config["services"].get(svc, {}).get("image", "")
        expected_digest = expected_ref.split("@", 1)[1] if "@" in expected_ref else None
        inspect = json.loads(_out("docker", "image", "inspect", c["ImageID"]) or "[{}]")[0]
        repo_digests = [d.split("@", 1)[1] for d in inspect.get("RepoDigests", [])]
        images[svc] = {
            "image": c.get("Image"),
            "image_id": c["ImageID"],
            "repo_digests": repo_digests,
            "expected_digest": expected_digest,
            "arch": inspect.get("Architecture"),
        }
        if expected_digest is None or expected_digest not in repo_digests:
            mismatches.append(f"{svc}: expected {expected_digest}, running {repo_digests}")
    return images, mismatches


def other_containers(docker: Docker, k6_container: str) -> list[str]:
    project = load_pin().compose_project
    return sorted(
        n.lstrip("/")
        for c in docker.containers()
        if c.get("Labels", {}).get("com.docker.compose.project") != project
        for n in c.get("Names", [])
        if n.lstrip("/") != k6_container
    )


def service_settings(config: dict[str, Any]) -> dict[str, Any]:
    """Limits, tracing and metric export settings per service, from the resolved compose model."""
    limits: dict[str, Any] = {}
    sampler: dict[str, str] = {}
    export_ms: dict[str, str | None] = {}
    for name, s in sorted(config["services"].items()):
        lim = ((s.get("deploy") or {}).get("resources") or {}).get("limits") or {}
        env = s.get("environment") or {}
        limits[name] = {
            "memory_bytes": int(lim["memory"]) if lim.get("memory") else None,
            "cpus": lim.get("cpus"),
            "gomemlimit": env.get("GOMEMLIMIT"),
        }
        if any(k.startswith("OTEL_") for k in env):
            sampler[name] = env.get("OTEL_TRACES_SAMPLER") or "parentbased_always_on (SDK default)"
            export_ms[name] = env.get("OTEL_METRIC_EXPORT_INTERVAL")
    jaeger_env = config["services"].get("jaeger", {}).get("environment") or {}
    return {
        "resource_limits": limits,
        "tracing": {
            "sampler": sampler,
            "jaeger_memory_max_traces": jaeger_env.get("MEMORY_MAX_TRACES"),
        },
        "metric_intervals": {
            "sdk_export_interval_ms": export_ms,
            "docker_stats_receiver_s": "10 (receiver default, upstream config sets none)",
            "prometheus_scrape": "none: no scrape targets, all metrics arrive over OTLP",
            "k6": "not exported to Prometheus in Phase 1; raw output only",
        },
    }


def live_flags() -> dict[str, Any]:
    with urllib.request.urlopen(f"{SHOP}/feature/api/read", timeout=10) as r:
        flags = json.loads(r.read()).get("flags", {})
    return {k: v.get("defaultVariant") for k, v in sorted(flags.items())}


def loadgen_off(docker: Docker) -> bool:
    try:
        with urllib.request.urlopen(f"{SHOP}/loadgen/", timeout=10) as r:
            status = r.status
    except urllib.error.HTTPError as e:
        status = e.code
    return all(c.passed for c in check_loadgen(docker.containers(all_=True), status))


class ResourceSampler(threading.Thread):
    """Records the k6 container's CPU (cores) and memory from the Docker stats stream."""

    def __init__(self, docker: Docker, container: str, path: Path) -> None:
        super().__init__(daemon=True)
        self.docker, self.container, self.path = docker, container, path
        self.cores: list[float] = []
        self.mem: list[int] = []

    def run(self) -> None:
        prev: Sample | None = None
        start: Sample | None = None
        with self.path.open("w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["elapsed_s", "cpu_cores", "mem_bytes", "online_cpus"])
            try:
                for s in self.docker.stream(self.container):
                    start = start or s
                    if prev is not None and s.read > prev.read and s.cpu_ns > 0:
                        cores = cores_between(prev, s)
                        self.cores.append(cores)
                        self.mem.append(s.mem_bytes)
                        w.writerow(
                            [
                                round((s.read - start.read).total_seconds(), 3),
                                round(cores, 4),
                                s.mem_bytes,
                                s.online_cpus,
                            ]
                        )
                    prev = s
            except (OSError, RuntimeError) as e:
                print(f"[run] k6 resource sampling stopped: {e}", file=sys.stderr)

    def summary(self) -> dict[str, Any]:
        if not self.cores:
            return {"samples": 0}
        return {
            "samples": len(self.cores),
            "cpu_cores_mean": round(sum(self.cores) / len(self.cores), 4),
            "cpu_cores_max": round(max(self.cores), 4),
            "mem_bytes_max": max(self.mem),
            "file": "k6-resources.csv",
        }


def run(opts: RunOptions) -> int:
    def say(msg: str) -> None:
        print(f"[run] {msg}", file=sys.stderr, flush=True)

    if platform.system() != "Darwin":
        say("the runner captures macOS laptop conditions and only supports macOS")
        return 2
    script = K6_DIR / opts.scenario
    if not script.is_file() or K6_DIR not in script.resolve().parents:
        say(f"no such script under k6/: {opts.scenario}")
        return 2

    pin = load_pin()
    run_id = make_run_id(opts.scenario)
    container = f"k6-{run_id}"
    started = datetime.now(UTC)
    commit, dirty = git_state()  # before the run directory exists
    caffeinate = subprocess.Popen(["caffeinate", "-d", "-i", "-w", str(os.getpid())])

    reset_report: dict[str, Any] = {"ran": False}
    reset_failures: list[str] = []
    if not opts.skip_reset:
        rep = reset()
        reset_report = {"ran": True, **rep.to_json()}
        reset_failures = rep.failures()

    docker = Docker()
    config = compose.resolved_config()
    say("capturing laptop conditions")
    before = conditions.capture()
    images, mismatches = images_and_mismatches(docker, config)
    dfacts = docker_facts()
    facts_pre = RunFacts(
        reset_ran=not opts.skip_reset,
        reset_failures=reset_failures,
        loadgen_off=loadgen_off(docker),
        conditions_before=before,
        conditions_after=before,
        other_containers=other_containers(docker, container),
        git_dirty_files=dirty,
        digest_mismatches=mismatches,
        docker_memory_bytes=int(dfacts["vm_memory_bytes"] or 0),
        usage_report_disabled=True,
        display_sleep_prevented=caffeinate.poll() is None,
    )
    pre_reasons = invalid_reasons(facts_pre)
    if opts.require_valid and pre_reasons:
        say("run aborted before sending load (--require-valid):")
        for r in pre_reasons:
            say(f"  - {r}")
        caffeinate.terminate()
        return 3

    out_dir = RESULTS_DIR / run_id
    out_dir.mkdir(parents=True)
    (out_dir / "reset.json").write_text(json.dumps(reset_report, indent=2) + "\n")
    env = script_env(run_id, opts.env)
    create = k6_command(
        image=pin.k6_image,
        network=pin.network,
        container=container,
        scenario=opts.scenario,
        results=out_dir,
        env=env,
        k6_args=opts.k6_args,
    )
    k6_version = _out("docker", "run", "--rm", "--network", "none", pin.k6_image, "version")
    flags = live_flags()

    say(f"run {run_id}: starting k6 ({pin.k6_image.split('@')[0]}) on network {pin.network}")
    subprocess.run(create, check=True, capture_output=True)
    k6_started = datetime.now(UTC)
    subprocess.run(["docker", "start", container], check=True, capture_output=True)
    sampler = ResourceSampler(docker, container, out_dir / "k6-resources.csv")
    sampler.start()
    with (out_dir / "k6-stdout.log").open("w") as log:
        proc = subprocess.Popen(
            ["docker", "logs", "--follow", container],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        assert proc.stdout is not None
        for line in proc.stdout:
            sys.stdout.write(line)
            log.write(line)
        proc.wait()
    sys.stdout.flush()
    exit_code = int(_out("docker", "wait", container) or -1)
    k6_finished = datetime.now(UTC)
    sampler.join(timeout=10)
    subprocess.run(["docker", "rm", container], check=False, capture_output=True)

    if (out_dir / RAW_FILE).exists():
        try:
            sys.stdout.write(report.text(report.write(out_dir)))
        except (OSError, ValueError, KeyError) as e:  # never lose a run to a report bug
            say(f"report failed ({e}); rebuild it with: perflab report {out_dir}")

    say("capturing laptop conditions after the run")
    after = conditions.capture()
    display_ok = caffeinate.poll() is None
    caffeinate.terminate()
    facts = replace(
        facts_pre,
        conditions_after=after,
        display_sleep_prevented=display_ok,
        events_during_run=conditions.power_log_events(k6_started, datetime.now(UTC)),
    )
    reasons = invalid_reasons(facts)

    manifest: dict[str, Any] = {
        "schema": 1,
        "run_id": run_id,
        **summarize(reasons),
        "scenario": opts.scenario,
        "experiment": opts.experiment,
        "started_at": started.isoformat(),
        "k6_started_at": k6_started.isoformat(),
        "k6_finished_at": k6_finished.isoformat(),
        "finished_at": datetime.now(UTC).isoformat(),
        "command": {"perflab": sys.argv, "k6_container": create},
        "git": {"commit": commit, "dirty": bool(dirty), "dirty_files": dirty},
        "k6": {
            "image": pin.k6_image,
            "version": k6_version,
            "extensions": [],
            "location": "container",
            "network": pin.network,
            "target": TARGET_URL,
            "env": env,
            "exit_code": exit_code,
            "process_resources": sampler.summary(),
        },
        "request_timeout_ms": int(env["TIMEOUT_MS"]),
        "warmup_excluded": None,
        "warmup_note": "no warm-up window defined yet (Phase 4.5); nothing excluded",
        "demo": {
            "version": pin.tag,
            "commit": pin.commit,
            "compose_project": pin.compose_project,
            "compose_args": compose.base_args(pin)[2:],
            "images": images,
            "digest_mismatches": mismatches,
        },
        "feature_flags": flags,
        **service_settings(config),
        "reset": {
            "ran": reset_report["ran"],
            "passed": reset_report.get("passed"),
            "file": "reset.json",
        },
        "loadgen_confirmed_off": facts.loadgen_off,
        "host": {**conditions.host_details(), "docker": dfacts},
        "conditions": {
            "before": before.to_json(),
            "after": after.to_json(),
            "power_log_during_run": facts.events_during_run,
        },
        "other_containers": facts.other_containers,
        "files": [*sorted(p.name for p in out_dir.iterdir()), "manifest.json"],
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, default=str) + "\n")

    say(f"results: {out_dir.relative_to(ROOT)}  k6 exit {exit_code}")
    if reasons:
        say("INVALID for comparison:")
        for r in reasons:
            say(f"  - {r}")
    else:
        say("valid: all run conditions met")
    return exit_code
