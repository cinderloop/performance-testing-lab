# Performance testing lab

A local, reproducible lab for load testing the [OpenTelemetry Demo](https://github.com/open-telemetry/opentelemetry-demo) (3.1.0) with [k6](https://k6.io) (2.3.0) on one laptop.

> **Results from this lab are relative, not absolute.** The app, its observability stack and k6 share one machine. Use the numbers to compare runs and diagnose problems, never as capacity claims. See [docs/environment.md](docs/environment.md).

Load is only ever sent to the local demo. A guard in every k6 script refuses any other host, and every tool is bound to `127.0.0.1`.

**Status:** Phase 1 (foundation) is done. Journeys, scenarios and experiments come in later phases.

## Quick start

Needs: macOS on Apple Silicon, Docker Desktop with **≥ 12 GB** of memory, Node 25.6.1, uv.

```bash
make setup      # pinned tooling + clone the pinned demo into demo/.upstream
make up         # start the demo (about 30 s once the images are pulled; the first pull is about 11 GB)
make reset      # reset protocol: fresh app state, verify it, health gate (about 1 min)
make run        # reset, then run the foundation check in a k6 container
make down       # stop and delete volumes
```

Each run writes `results/<run-id>/`: a manifest, raw per-request k6 data, the k6 summary, the k6 container's own CPU and memory, and the reset report ([ADR 0005](docs/decisions/0005-results-format.md)). Runs made under conditions that break the rules (battery power, other heavy apps, failed reset, uncommitted code …) are still written, but flagged `"valid": false` with the reasons.

UIs (loopback only): shop http://localhost:8080, Grafana http://localhost:8080/grafana/, Jaeger http://localhost:8080/jaeger/ui/, Prometheus http://localhost:9090.

`make check` runs everything CI runs: ESLint, Prettier, ruff, `tsc`, mypy (strict), `k6 inspect` on every script, the guard check inside k6, the unit tests and the port policy.

## Layout

| Path | Contents |
|---|---|
| `demo/` | demo-specific: pinned version, compose overrides, collector and SDK config ([demo/README.md](demo/README.md)) |
| `k6/lib/` | generic: config, local-target guard, HTTP client with tags and timeouts, checks, options, summary |
| `k6/scenarios/` | scenarios (Phase 1: `foundation-check.ts`, a pipeline check, not a workload) |
| `src/perflab/` | generic lab tooling: reset protocol, laptop conditions, runner, manifest, validity rules |
| `tests/` | unit tests: `tests/k6` (guard, config) and `tests/python` (reset checks, validity, parsers, runner) |
| `results/` | one directory per run |
| `docs/` | [spike findings](docs/spike-findings.md), [environment](docs/environment.md), [reset protocol](docs/reset-protocol.md), [decisions](docs/decisions/) |

## Decisions so far

| ADR | Decision |
|---|---|
| [0001](docs/decisions/0001-where-k6-runs.md) | k6 runs in a container on the demo network, pinned by digest |
| [0002](docs/decisions/0002-realistic-traffic.md) | which browser traffic the tests reproduce (no static assets; images opt-in) |
| [0003](docs/decisions/0003-go-memory-limits.md) | raised Go memory limits for product-catalog and checkout, plus a health gate |
| [0004](docs/decisions/0004-k6-language.md) | k6 scripts in TypeScript |
| [0005](docs/decisions/0005-results-format.md) | results layout and formats |
| [0006](docs/decisions/0006-analysis-in-python.md) | lab tooling and analysis in Python |
| [0007](docs/decisions/0007-statistics-unit.md) | the run is the unit for comparing configurations |
| [0008](docs/decisions/0008-request-timeouts.md) | explicit 10 s request timeout; timeouts are failures |
| [0009](docs/decisions/0009-local-only-guard-and-ports.md) | local-target guard and loopback-only ports |

## Credit

The system under test is the [OpenTelemetry Demo](https://github.com/open-telemetry/opentelemetry-demo), © The OpenTelemetry Authors, Apache License 2.0. It's used through its published images and configuration overrides; see [demo/README.md](demo/README.md).

## Licence

[MIT](LICENSE) © 2026 Ashen J. This covers this repository's own code and docs; the OpenTelemetry Demo stays under its own Apache 2.0 licence.
