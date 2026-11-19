/**
 * Options every lab script shares. Scenario scripts spread their own `scenarios` and
 * `thresholds` over these.
 */

import type { Options } from "k6/options";

import type { LabConfig } from "./config.ts";
import { SYSTEM_TAGS } from "./tags.ts";

export const SUMMARY_TREND_STATS: readonly string[] = [
  "count",
  "avg",
  "min",
  "med",
  "p(90)",
  "p(95)",
  "p(99)",
  "max",
];

/**
 * k6 only puts a sub-metric in the end-of-test summary when a threshold references it, so these
 * always-true thresholds make successes and failures appear separately in every summary.
 * Real pass/fail thresholds are added per scenario (docs/thresholds.md, Phase 2).
 */
export const SUMMARY_SUBMETRICS: Readonly<Record<string, string[]>> = {
  "http_req_duration{expected_response:true}": ["max>=0"],
  "http_req_duration{expected_response:false}": ["max>=0"],
};

export function labOptions(config: LabConfig, own: Options): Options {
  return {
    ...own,
    systemTags: [...SYSTEM_TAGS],
    tags: { ...own.tags, run_id: config.runId },
    summaryTrendStats: [...SUMMARY_TREND_STATS],
    thresholds: { ...SUMMARY_SUBMETRICS, ...own.thresholds },
    // Don't follow redirects silently: a redirect is a different request, tagged and counted.
    maxRedirects: 0,
  };
}
