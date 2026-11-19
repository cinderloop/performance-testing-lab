# Performance testing lab

A local lab for load testing the [OpenTelemetry Demo](https://github.com/open-telemetry/opentelemetry-demo) (3.1.0) with [k6](https://k6.io), on one laptop.

Status: the Phase 0 spike is done; Phase 1 hasn't started.

- [`docs/spike-findings.md`](docs/spike-findings.md): what the spike found, with commands and payloads
- [`docs/decisions/`](docs/decisions/): architecture decision records

Load is only ever sent to the local demo.
