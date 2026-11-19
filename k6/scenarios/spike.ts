/**
 * SPIKE: what happens when traffic jumps suddenly, and how fast does the system recover?
 *
 * Load: open model. Baseline at LOAD_PER_MIN, a 10 s surge to 1.25× the measured breakpoint, held
 * for 1 min, a 10 s drop back to LOAD_PER_MIN, then a 6 min recovery period.
 * Pass: back to baseline latency and error rate within the recovery period (docs/thresholds.md).
 */

import { labOptions } from "../lib/options.ts";
import { plan, stages, vusFor, peakPerMin } from "../lib/phases.ts";
import {
  config,
  handleSummaryWithPlan,
  runSession,
  SESSION_S_ESTIMATE,
  setupClock,
} from "./common.ts";
import { BREAKPOINT_PER_MIN as B, LOAD_PER_MIN as L } from "./levels.ts";

const SPIKE = Math.round(1.25 * B);
const PLAN = plan("spike", "ramping-arrival-rate", 0, [
  { name: "ramp_up", durationS: 60, targetPerMin: L },
  { name: "baseline", durationS: 240, targetPerMin: L },
  { name: "surge", durationS: 10, targetPerMin: SPIKE },
  { name: "spike", durationS: 60, targetPerMin: SPIKE },
  { name: "drop", durationS: 10, targetPerMin: L },
  { name: "recovery", durationS: 360, targetPerMin: L },
]);

export const options = labOptions(config, {
  scenarios: {
    spike: {
      executor: "ramping-arrival-rate",
      startRate: 0,
      timeUnit: "1m",
      stages: stages(PLAN),
      preAllocatedVUs: vusFor(peakPerMin(PLAN), SESSION_S_ESTIMATE, 1),
      maxVUs: vusFor(peakPerMin(PLAN), SESSION_S_ESTIMATE, 3),
      gracefulStop: "30s",
    },
  },
});

export const setup = setupClock;
export default function (): void {
  runSession();
}
export const handleSummary = handleSummaryWithPlan(PLAN);
