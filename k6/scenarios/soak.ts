/**
 * SOAK: does anything degrade over time at normal load (memory growth, slow leaks, queue build-up)?
 *
 * Load: open model, 2 min ramp, then 60 min at LOAD_PER_MIN. Why 60 min on a laptop: see
 * docs/workload-model.md ("Soak duration").
 * Pass: provisional thresholds over the whole run, plus no upward trend in success p95 between
 * the first and last 10 minutes of the steady phase (computed by `perflab report`).
 */

import { labOptions } from "../lib/options.ts";
import { plan, stages, vusFor, peakPerMin } from "../lib/phases.ts";
import { PROVISIONAL_THRESHOLDS } from "../lib/thresholds.ts";
import {
  config,
  handleSummaryWithPlan,
  runSession,
  SESSION_S_ESTIMATE,
  setupClock,
} from "./common.ts";
import { LOAD_PER_MIN } from "./levels.ts";

const PLAN = plan("soak", "ramping-arrival-rate", 0, [
  { name: "ramp_up", durationS: 120, targetPerMin: LOAD_PER_MIN },
  { name: "steady", durationS: 3600, targetPerMin: LOAD_PER_MIN },
]);

export const options = labOptions(config, {
  scenarios: {
    soak: {
      executor: "ramping-arrival-rate",
      startRate: 0,
      timeUnit: "1m",
      stages: stages(PLAN),
      preAllocatedVUs: vusFor(peakPerMin(PLAN), SESSION_S_ESTIMATE, 1),
      maxVUs: vusFor(peakPerMin(PLAN), SESSION_S_ESTIMATE, 3),
      gracefulStop: "30s",
    },
  },
  thresholds: { ...PROVISIONAL_THRESHOLDS },
});

export const setup = setupClock;
export default function (): void {
  runSession();
}
export const handleSummary = handleSummaryWithPlan(PLAN);
