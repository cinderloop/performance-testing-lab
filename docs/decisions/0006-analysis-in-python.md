# ADR 0006: Analysis and lab tooling in Python

- Status: **Accepted** (2026-11-20, Phase 1)

## Context

Two kinds of code sit around k6:
- **Lab tooling:** start and reset the demo, capture laptop conditions, run k6, write the manifest.
- **Analysis (Phase 4 on):** percentiles from raw data, bootstrap confidence intervals, Little's Law, warm-up detection, charts.

The plan names Python with uv, ruff, pytest and pandas/numpy/scipy/matplotlib for analysis.

## Decision

Both live in Python 3.14 (pinned with `.python-version`, 3.14.8), managed by uv with `uv.lock` committed.

- **Lab tooling** is the `perflab` package (`src/perflab/`). It uses only the standard library: Docker is reached through `docker`/`docker compose` and the Docker Engine API over the local unix socket, and the macOS signals through `pmset`, `top`, `sysctl` and `swift`. Fewer dependencies means fewer things to pin and audit.
- **Analysis** comes in Phase 4 as a separate `analysis/` package, adding pandas, numpy, scipy and matplotlib, all pinned through the lock file.
- Type checking uses **mypy `--strict`** (2.4.1). The plan allows pyright or mypy. mypy installs as an ordinary Python package; pyright's PyPI wrapper downloads a Node build at run time, which is harder to pin.
- ruff (lint + format) and pytest run in CI. `demo/.upstream` is excluded from every tool.

## Consequences

- The runner is macOS-only, because it captures macOS laptop conditions. Linux readers can still use the k6 scripts and reset protocol. `docs/adapting-to-your-system.md` (Phase 6) will say how.
- Pure logic (validity rules, reset checks, parsers, the port policy, the k6 command builder) is separated from I/O and unit-tested.
