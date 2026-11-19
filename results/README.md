# Results

One directory per run, written by `perflab run` ([ADR 0005](../docs/decisions/0005-results-format.md)). Check `manifest.json` → `valid` before using a run: invalid runs are kept for honesty but never used for comparison.

Committed per run: `manifest.json`, `samples.csv.gz` (every request, from k6's raw output), `report.json`, `reset.json`, `scenario-plan.json`, `k6-summary.json`, `k6-resources.csv`, `k6-stdout.log`, `raw_archive.json`. The full `k6-raw.json.gz` is too big for git; it's attached to the phase's GitHub Release, and `raw_archive.json` has its SHA-256 ([ADR 0005](../docs/decisions/0005-results-format.md)).
