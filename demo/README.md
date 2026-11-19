# demo/: the system under test

This directory holds only **configuration** for the [OpenTelemetry Demo](https://github.com/open-telemetry/opentelemetry-demo) ("Astronomy Shop"). The demo itself isn't copied into this repo. `make fetch` clones the pinned release into `demo/.upstream/` (git-ignored), and Docker pulls its published images by digest.

| File | What it does |
|---|---|
| `pin.json` | Demo release (3.1.0), its git commit, the compose files used, the Docker network, the k6 image digest |
| `demo.env` | Pins `DEMO_VERSION` / `IMAGE_VERSION` (upstream defaults to `latest`), points the collector at our extras file |
| `compose.images.yaml` | Every image as `tag@sha256:digest` |
| `compose.lab.yaml` | Loopback-only ports, load generator never started, memory limits, 10 s metric export |
| `config/otel-config.yml` | product-catalog SDK config: upstream's file plus a configurable metric interval |
| `config/otelcol-config-extras.yml` | Collector overrides through upstream's extras seam: span-metrics flush and `docker_stats` interval |

Commands (from the repo root): `make fetch`, `make up`, `make reset`, `make down`, `make ports`. See [docs/environment.md](../docs/environment.md) and [docs/reset-protocol.md](../docs/reset-protocol.md).

## Credit and licence

The OpenTelemetry Demo is © The OpenTelemetry Authors and licensed under the **Apache License 2.0**. `config/otel-config.yml` is a modified copy of the demo's `otel-config.yml`: a file header and one `interval` line were added, and the file says so. Everything else here is original lab configuration that refers to upstream files without copying them.
