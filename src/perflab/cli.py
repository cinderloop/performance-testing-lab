"""`perflab` command line: one command each to fetch, start, stop and reset the demo, and to run."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from analysis import report
from perflab import compose
from perflab.paths import K6_DIR, UPSTREAM_DIR, load_pin
from perflab.ports import port_violations, published_ports
from perflab.reset import reset
from perflab.runner import RunOptions, run


def cmd_fetch(_: argparse.Namespace) -> int:
    """Clone the pinned demo into demo/.upstream (not committed) and verify the commit."""
    pin = load_pin()
    if not UPSTREAM_DIR.exists():
        subprocess.run(
            [
                "git",
                "clone",
                "--quiet",
                "--depth",
                "1",
                "--branch",
                pin.tag,
                pin.repo,
                str(UPSTREAM_DIR),
            ],
            check=True,
        )
    head = subprocess.run(
        ["git", "-C", str(UPSTREAM_DIR), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if head != pin.commit:
        print(
            f"demo/.upstream is at {head}, expected {pin.commit} (tag {pin.tag})", file=sys.stderr
        )
        return 1
    print(f"opentelemetry-demo {pin.tag} at {head}")
    return 0


def cmd_ports(_: argparse.Namespace) -> int:
    """Fail if any published port isn't bound to 127.0.0.1 (ground rule 4)."""
    config = compose.resolved_config()
    problems = port_violations(config)
    for line in published_ports(config):
        print(f"published {line}")
    for p in problems:
        print(f"VIOLATION {p}", file=sys.stderr)
    if "load-generator" in config.get("services", {}):
        print("VIOLATION load-generator is part of the default configuration", file=sys.stderr)
        return 1
    return 1 if problems else 0


SCRIPT_DIRS = ("scenarios", "experiments")
GUARD_PROBE_URL = "https://example.com"


def cmd_inspect(_: argparse.Namespace) -> int:
    """`k6 inspect` every script, then prove the guard fires inside real k6 at init.

    Runs with `--network none`, so nothing can leave the container even if the guard failed.
    """
    image = load_pin().k6_image
    base = [
        "docker",
        "run",
        "--rm",
        "--network",
        "none",
        "-e",
        "K6_NO_USAGE_REPORT=true",
        "-v",
        f"{K6_DIR}:/k6:ro",
    ]
    # Entry scripts only: modules that declare k6 options (helpers like common.ts don't).
    scripts = sorted(
        p
        for d in SCRIPT_DIRS
        for p in (K6_DIR / d).rglob("*.ts")
        if "export const options" in p.read_text()
    )
    failed = 0
    for script in scripts:
        rel = script.relative_to(K6_DIR)
        r = subprocess.run(
            [*base, image, "inspect", f"/k6/{rel}"], capture_output=True, text=True, check=False
        )
        print(f"{'ok  ' if r.returncode == 0 else 'FAIL'} k6 inspect {rel}")
        if r.returncode != 0:
            failed += 1
            print(r.stderr or r.stdout, file=sys.stderr)
    for script in scripts:
        rel = script.relative_to(K6_DIR)
        r = subprocess.run(
            [*base, image, "inspect", "-e", f"BASE_URL={GUARD_PROBE_URL}", f"/k6/{rel}"],
            capture_output=True,
            text=True,
            check=False,
        )
        blocked = r.returncode != 0 and "refusing non-local target" in (r.stderr + r.stdout)
        print(f"{'ok  ' if blocked else 'FAIL'} guard blocks BASE_URL={GUARD_PROBE_URL} in {rel}")
        failed += 0 if blocked else 1
    if not scripts:
        print("no k6 scripts found", file=sys.stderr)
        return 1
    return 1 if failed else 0


def cmd_up(_: argparse.Namespace) -> int:
    if cmd_ports(_) != 0:
        return 1
    compose.run("up", "--detach", "--wait", "--wait-timeout", "600")
    print(
        "Shop http://localhost:8080  Grafana http://localhost:8080/grafana/  "
        "Jaeger http://localhost:8080/jaeger/ui/  Prometheus http://localhost:9090"
    )
    return 0


def cmd_down(_: argparse.Namespace) -> int:
    compose.run("down", "--volumes", "--remove-orphans")
    return 0


def cmd_reset(args: argparse.Namespace) -> int:
    report = reset()
    if args.json:
        print(json.dumps(report.to_json(), indent=2))
    return 0 if report.passed else 1


def cmd_report(args: argparse.Namespace) -> int:
    """Rebuild report.json for a run from its raw data."""
    run_dir = Path(args.run_dir)
    if not any((run_dir / f).exists() for f in ("samples.csv.gz", "k6-raw.json.gz")):
        print(f"no samples.csv.gz or k6-raw.json.gz in {run_dir}", file=sys.stderr)
        return 2
    print(report.text(report.write(run_dir)), end="")
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    return run(
        RunOptions(
            scenario=args.scenario,
            experiment=args.experiment,
            skip_reset=args.skip_reset,
            require_valid=args.require_valid,
            k6_args=args.k6_args,
            env=dict(kv.split("=", 1) for kv in args.env),
        )
    )


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="perflab", description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("fetch", help="clone the pinned demo into demo/.upstream").set_defaults(
        f=cmd_fetch
    )
    sub.add_parser("ports", help="check that every published port is loopback-only").set_defaults(
        f=cmd_ports
    )
    sub.add_parser("inspect", help="k6 inspect every script and check the guard").set_defaults(
        f=cmd_inspect
    )
    sub.add_parser("up", help="start the demo (load generator never started)").set_defaults(
        f=cmd_up
    )
    sub.add_parser("down", help="stop the demo and delete its volumes").set_defaults(f=cmd_down)
    r = sub.add_parser("reset", help="run the reset protocol and verify the start state")
    r.add_argument("--json", action="store_true", help="print the full reset report")
    r.set_defaults(f=cmd_reset)
    rep = sub.add_parser("report", help="(re)build report.json for a run from its raw data")
    rep.add_argument("run_dir", help="results/<run-id>")
    rep.set_defaults(f=cmd_report)
    run_p = sub.add_parser(
        "run", help="reset, run a k6 scenario in a container, write results/<run-id>/"
    )
    run_p.add_argument("scenario", help="script under k6/, e.g. scenarios/smoke.ts")
    run_p.add_argument("--experiment", default=None, help="experiment name for the manifest")
    run_p.add_argument(
        "--skip-reset", action="store_true", help="don't reset (the run is marked invalid)"
    )
    run_p.add_argument(
        "--require-valid",
        action="store_true",
        help="abort before sending load if pre-run conditions make the run invalid",
    )
    run_p.add_argument(
        "--env",
        "-e",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="extra environment for the k6 script (recorded in the manifest)",
    )
    run_p.add_argument("k6_args", nargs=argparse.REMAINDER, help="extra k6 arguments after --")
    run_p.set_defaults(f=cmd_run)
    args = p.parse_args(argv)
    if getattr(args, "k6_args", None) and args.k6_args[0] == "--":
        args.k6_args = args.k6_args[1:]
    code: int = args.f(args)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
