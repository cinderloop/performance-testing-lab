/**
 * BREAKPOINT: at what arrival rate does the baseline stop keeping up?
 *
 * Load: open model, a linear ramp from 0 to MAX_PER_MIN over 30 min.
 * Stop condition: k6 aborts the test (abortOnFail) when the error rate exceeds 5%, when success
 * p95 exceeds 3 s, or when more than 100 sessions couldn't start (VUs exhausted). k6 evaluates
 * thresholds cumulatively, so the abort lags the real breaking point. The breakpoint itself is
 * computed afterwards from 10 s windows in the raw data (`perflab report`, docs/thresholds.md).
 * The ramp's end also bounds the run, so it always finishes.
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

/**
 * Upper bound of the ramp. The first run (to 3000/min) never failed the thresholds, with errors
 * only starting near the top, so the ceiling is doubled (docs/scenarios.md).
 */
export const MAX_PER_MIN = 6000;

const PLAN = plan("breakpoint", "ramping-arrival-rate", 0, [
  { name: "ramp", durationS: 1800, targetPerMin: MAX_PER_MIN },
]);

const abort = (threshold: string) => ({ threshold, abortOnFail: true, delayAbortEval: "60s" });

export const options = labOptions(config, {
  scenarios: {
    breakpoint: {
      executor: "ramping-arrival-rate",
      startRate: 0,
      timeUnit: "1m",
      stages: stages(PLAN),
      preAllocatedVUs: vusFor(peakPerMin(PLAN), SESSION_S_ESTIMATE, 0.5),
      maxVUs: vusFor(peakPerMin(PLAN), SESSION_S_ESTIMATE, 1.5),
      gracefulStop: "30s",
    },
  },
  thresholds: {
    http_req_failed: [abort("rate<0.05")],
    "http_req_duration{expected_response:true}": [abort("p(95)<3000")],
    dropped_iterations: [abort("count<100")],
  },
});

export const setup = setupClock;
export default function (): void {
  runSession();
}
export const handleSummary = handleSummaryWithPlan(PLAN);
