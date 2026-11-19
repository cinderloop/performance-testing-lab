# Environment

What this lab runs on, how it's controlled, and what its results can and can't show.

> **Results are relative, never absolute.** The app, its observability stack and k6 all share one laptop. Numbers from this lab compare runs and help diagnose problems; they are not capacity claims about the OpenTelemetry Demo or any real system.

## Machine

| | |
|---|---|
| Host | Apple M4 Max, 16 cores, 64 GB RAM, macOS 26.0 (25A354) |
| Docker | Docker Desktop 4.95.0, Engine 29.8.2, Compose 5.6.0 |
| Docker VM | 16 vCPUs, **≥ 12 GB memory** (set in Docker Desktop. Below 12 GB, runs are invalid) |
| System under test | OpenTelemetry Demo **3.1.0** (`dedc0178`), every image pinned by digest |
| Load generator | k6 **2.3.0** in a container on the demo network (ADR 0001), `grafana/k6@sha256:2dd4756e…` |

Every run's `manifest.json` records the actual values (`host`, `host.docker`, `demo.images`, `k6`). This table is just a summary.

## How the demo is configured

The demo is used through its published images and configuration overrides. Its source isn't copied into this repo. `make fetch` clones tag 3.1.0 into `demo/.upstream/` (git-ignored) and verifies the commit.

| File | Purpose |
|---|---|
| `demo/pin.json` | demo repo, tag, commit, compose files, network, k6 image digest |
| `demo/demo.env` | `DEMO_VERSION=3.1.0`, `IMAGE_VERSION=3.1.0` (upstream defaults to `latest`), collector extras path |
| `demo/compose.images.yaml` | every image as `tag@sha256:digest` |
| `demo/compose.lab.yaml` | ports, load generator off, memory limits, 10 s SDK metric export |
| `demo/config/otel-config.yml` | product-catalog's declarative SDK config with a configurable metric interval |
| `demo/config/otelcol-config-extras.yml` | collector: span-metrics flush and `docker_stats` interval 10 s |

Applied in that order: the upstream `.env` and compose files, then ours. See [demo/README.md](../demo/README.md).

### Ports (ground rule 4)

Only three ports are published, all on loopback ([ADR 0009](decisions/0009-local-only-guard-and-ports.md)):

| Address | What |
|---|---|
| `127.0.0.1:8080` | shop, `/grafana/`, `/jaeger/ui/`, `/feature/` (flagd-ui) |
| `127.0.0.1:10000` | Envoy admin (request counters for the reset protocol) |
| `127.0.0.1:9090` | Prometheus |

`make ports` (also in CI) fails if any other port, or any non-loopback binding, appears in the resolved config.

### Resource limits

Upstream's memory limits are kept, except for these:

| Service | Upstream | Lab | Why |
|---|---|---|---|
| product-catalog, checkout | 20M, `GOMEMLIMIT=16MiB` | **64M, `GOMEMLIMIT=48MiB`** | GC death spiral at idle ([ADR 0003](decisions/0003-go-memory-limits.md)) |
| opensearch | 1024M | 1536M | 99% of its limit at idle (spike §3) |
| kafka | 620M | 800M | 93% of its limit at idle |

No service has a CPU limit (upstream sets none), so any container can use all 16 vCPUs. Experiments that need saturation add CPU limits explicitly and record them. The manifest's `resource_limits` lists every service's effective limits.

## Metric resolution

**Prometheus scrapes nothing.** Every metric is pushed over OTLP, so the plan's "scrape interval" really means export or collection intervals. As configured and measured (sample spacing in Prometheus, 2026-11-20):

| Source | Interval | Covers |
|---|---|---|
| App SDK metrics | **10 s** (`OTEL_METRIC_EXPORT_INTERVAL=10000`, measured 10 s) | accounting, ad, cart, checkout, fraud-detection, kafka, payment, product-catalog, recommendation |
| frontend SDK metrics | **60 s** (measured) | frontend. Its `Instrumentation.js` builds the metric reader in code, so the env var can't change it, and changing it would mean overriding upstream source. Use span metrics for frontend RED. |
| Span metrics (`traces_span_metrics_*`, from traces) | **10 s** (lab collector override, measured 10 s) | RED for every traced service, including those whose SDKs export no metrics (currency, email, quote, shipping, flagd, frontend-proxy …) |
| `docker_stats` (container CPU, memory, network, block I/O) | **10 s** (explicit in the lab collector config, measured 10 s) | USE per container, including the k6 container |
| k6 | not exported in Phase 1 | Phase 3 adds k6 → Prometheus (spike §10). Analysis always uses k6's raw output |

Consequence: **don't draw conclusions finer than 10 s from server-side data** (60 s for frontend SDK metrics). k6's raw data has per-request resolution. When comparing the two, align time windows explicitly. The manifest's `metric_intervals` records the configured values.

**Known upstream noise:** Prometheus logs `empty data points … is dropped` every 10 s for some SDK self-metrics (`otel.sdk.span.started` and others). Those metrics are dropped; the rest of each batch is ingested. One batch (4 items) was rejected with HTTP 500 right after a collector restart. To revisit in Phase 3.

## Tracing

- Every SDK samples **100%** (no `OTEL_TRACES_SAMPLER` set: parent-based always-on).
- Jaeger stores traces **in memory, capped at 25,000**, so under load old traces are evicted within minutes.
- The collector also runs the `debug` exporter on every pipeline.

All of this is observer overhead and is the subject of Phase 5.2. The manifest records the sampler per service and the Jaeger cap.

## Laptop conditions (ground rule 8)

The runner captures these **before and after** every run, without sudo:

| Signal | Source | Valid when |
|---|---|---|
| Power source | `pmset -g batt` | `AC Power` |
| Low Power Mode | `ProcessInfo.isLowPowerModeEnabled` (via `swift -e`) | `false` |
| Thermal state | `ProcessInfo.thermalState` | `0` (nominal) |
| Thermal/performance warnings | `pmset -g therm` | recorded |
| Power mode setting | `pmset -g` → `powermode` | recorded |
| Load average | `sysctl vm.loadavg` | recorded |
| Busy processes | `top -l 2 -s 2` (2 s CPU sample, top 15) | no non-lab process ≥ 25% CPU |
| Heavy applications | `ps` against a list (Chrome, Transmission, Firefox, Slack, Zoom, Teams, Spotify) | none running |
| Display/system sleep | the runner holds `caffeinate -d -i -w <pid>` for the whole run | assertion held |
| Sleep, wake, battery **during** the run | `pmset -g log` entries between k6 start and end | none |

**Not captured** (they need `sudo powermetrics`): CPU frequency, die temperature, power draw. Every manifest lists them under `conditions.*.not_captured`. Thermal state is the only throttling signal available. It's coarse: it moves only when macOS is already reacting.

Lab processes that never count as "busy": Docker Desktop and its VM process (`com.docker.*`, `com.apple.Virtualization…`), the runner, `top`, `caffeinate`, and core macOS processes (`kernel_task`, `WindowServer`, `launchd`, `sysmond`).

## When a run is invalid

`perflab run` always writes the run, but sets `valid: false` and lists every reason when any of these hold (`src/perflab/validity.py`, unit-tested rule by rule):

- the reset protocol didn't run, or any of its checks failed
- the demo's load generator wasn't confirmed off
- not on mains power, Low Power Mode on or unknown, thermal state not nominal (before **or** after)
- a heavy application was running, or a non-lab process used ≥ 25% CPU
- containers other than the demo and this run's k6 were running
- the repo had uncommitted changes, so the commit doesn't describe the code that ran
- an image's digest doesn't match `demo/compose.images.yaml`
- Docker VM memory below 12 GB
- the power log (`pmset -g log`) shows the Mac slept, woke or ran on battery **at any time during the run**. Checking only before and after misses this, and `caffeinate` can't prevent lid-closed (clamshell) sleep on battery
- k6 usage reporting not disabled, or `caffeinate` not held

`perflab run --require-valid` aborts **before sending any load** if the pre-run checks already make the run invalid. Invalid runs are kept but never used for comparison, as the definition of done requires.

## Tags

Every k6 sample carries these (`k6/lib/tags.ts`):

| Tag | Values |
|---|---|
| `name` | endpoint id, e.g. `page_home`, `api_products_list`, `api_cart_get` |
| `endpoint_group` | `page`, `api`, `flags`, `image` |
| `expected_response` | `true` / `false`: success or failure as declared per request (default: only 200 is a success) |
| `status`, `method`, `error`, `error_code`, `scenario`, `group`, `check`, `proto` | k6 system tags |
| `run_id` | the run |
| `journey`, `step` | from Phase 2 |

`url` is dropped on purpose: it contains per-user query strings (spike §10).
