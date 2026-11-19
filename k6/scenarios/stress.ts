/**
 * STRESS: how does the system fail beyond its breakpoint, and how fast does it recover?
 *
 * Load: open model. Baseline at LOAD_PER_MIN, then steps at 0.75, 1.0, 1.25 and 1.5× the measured
 * breakpoint (3 min each), then straight back to LOAD_PER_MIN for a 6 min recovery period.
 * Pass: the system returns to baseline latency and error rate within the recovery period
 * (criterion in docs/thresholds.md, computed by `perflab report`). Latency thresholds are not
 * pass criteria here: exceeding them is the point.
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

const r = Math.round;
const PLAN = plan("stress", "ramping-arrival-rate", 0, [
  { name: "ramp_up", durationS: 60, targetPerMin: L },
  { name: "baseline", durationS: 240, targetPerMin: L },
  { name: "to_0.75B", durationS: 30, targetPerMin: r(0.75 * B) },
  { name: "at_0.75B", durationS: 180, targetPerMin: r(0.75 * B) },
  { name: "to_1.0B", durationS: 30, targetPerMin: B },
  { name: "at_1.0B", durationS: 180, targetPerMin: B },
  { name: "to_1.25B", durationS: 30, targetPerMin: r(1.25 * B) },
  { name: "at_1.25B", durationS: 180, targetPerMin: r(1.25 * B) },
  { name: "to_1.5B", durationS: 30, targetPerMin: r(1.5 * B) },
  { name: "at_1.5B", durationS: 180, targetPerMin: r(1.5 * B) },
  { name: "drop", durationS: 10, targetPerMin: L },
  { name: "recovery", durationS: 360, targetPerMin: L },
]);

export const options = labOptions(config, {
  scenarios: {
    stress: {
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
