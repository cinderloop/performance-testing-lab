/**
 * Consistent end-of-test summary (ADR 0005).
 *
 * Writes k6's summary data unchanged to `<resultsDir>/k6-summary.json` and prints a short text
 * summary that never shows a latency without saying whether it's successes or failures.
 * The summary is a convenience. Analysis always uses the raw per-request output
 * (`k6-raw.json.gz`), because these percentiles are per run and can't be combined.
 */

import type { LabConfig } from "./config.ts";

interface MetricSummary {
  type: string;
  values: Record<string, number | null | undefined>;
  thresholds?: Record<string, { ok: boolean }>;
}

interface SummaryData {
  metrics: Record<string, MetricSummary | undefined>;
  state: { testRunDurationMs: number };
}

function fmt(v: number | null | undefined, digits = 1): string {
  return typeof v === "number" && Number.isFinite(v) ? v.toFixed(digits) : "-";
}

function trendLine(label: string, m: MetricSummary | undefined): string {
  if (m === undefined || !m.values.count) {
    return `  ${label.padEnd(26)} n=0`;
  }
  const v = m.values;
  return (
    `  ${label.padEnd(26)} n=${v.count ?? 0}  med=${fmt(v.med)}  p95=${fmt(v["p(95)"])}  ` +
    `p99=${fmt(v["p(99)"])}  max=${fmt(v.max)} ms`
  );
}

export function textSummary(data: SummaryData, runId: string): string {
  const m = data.metrics;
  const reqs = m.http_reqs?.values;
  const failed = m.http_req_failed?.values;
  const checks = m.checks?.values;
  const dropped = m.dropped_iterations?.values.count ?? 0;
  const lines = [
    `run ${runId}: ${fmt(data.state.testRunDurationMs / 1000)} s`,
    `  requests                   ${reqs?.count ?? 0} (${fmt(reqs?.rate)}/s)`,
    `  failed requests            ${failed?.passes ?? 0} (${fmt((failed?.rate ?? 0) * 100, 2)}%)`,
    trendLine("duration, successes", m["http_req_duration{expected_response:true}"]),
    trendLine("duration, failures", m["http_req_duration{expected_response:false}"]),
    `  checks passed              ${checks?.passes ?? 0}/${(checks?.passes ?? 0) + (checks?.fails ?? 0)}`,
    `  iterations                 ${m.iterations?.values.count ?? 0}, dropped ${dropped}`,
  ];
  const broken = Object.entries(m)
    .flatMap(([name, s]) =>
      Object.entries(s?.thresholds ?? {})
        .filter(([, t]) => !t.ok)
        .map(([expr]) => `${name}: ${expr}`),
    )
    .sort();
  lines.push(broken.length ? `  thresholds FAILED: ${broken.join("; ")}` : "  thresholds passed");
  lines.push("  (raw per-request data: k6-raw.json.gz; use it, not these per-run percentiles)");
  return lines.join("\n") + "\n";
}

export function makeHandleSummary(config: LabConfig): (data: unknown) => Record<string, string> {
  return (data) => ({
    [`${config.resultsDir}/k6-summary.json`]: JSON.stringify(data, null, 2),
    stdout: textSummary(data as SummaryData, config.runId),
  });
}
