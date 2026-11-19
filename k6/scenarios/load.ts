/**
 * LOAD: does the system meet the provisional thresholds at normal load?
 *
 * Load: open model (ramping-arrival-rate), 2 min ramp to LOAD_PER_MIN, then 10 min steady.
 * Pass: provisional thresholds (error rate, checks, success p95 per endpoint group).
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

const PLAN = plan("load", "ramping-arrival-rate", 0, [
  { name: "ramp_up", durationS: 120, targetPerMin: LOAD_PER_MIN },
  { name: "steady", durationS: 600, targetPerMin: LOAD_PER_MIN },
]);

export const options = labOptions(config, {
  scenarios: {
    load: {
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
