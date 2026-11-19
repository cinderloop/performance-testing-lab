/**
 * Shared plumbing for the scenario scripts: config, client, the session function, setup() that
 * records the start time, and handleSummary that also writes `scenario-plan.json` for analysis.
 */

import { loadConfig } from "../lib/config.ts";
import { createClient } from "../lib/http.ts";
import type { ScenarioPlan } from "../lib/phases.ts";
import { makeHandleSummary } from "../lib/summary.ts";
import { session, type JourneyName } from "../journeys/journeys.ts";

export const config = loadConfig(__ENV);
export const client = createClient(config);

/** A generous estimate of one session's duration for VU sizing (Little's Law), seconds. */
export const SESSION_S_ESTIMATE = 20;

export interface SetupData {
  /** Epoch ms when setup finished, i.e. when the scenario's clock starts (the plan's t = 0). */
  t0Ms: number;
}

export function setupClock(): SetupData {
  return { t0Ms: Date.now() };
}

export function runSession(journey?: JourneyName): void {
  session(client, journey);
}

export function handleSummaryWithPlan(
  plan: ScenarioPlan | null,
): (data: unknown) => Record<string, string> {
  const base = makeHandleSummary(config);
  return (data) => {
    const setup = (data as { setup_data?: SetupData }).setup_data;
    return {
      ...base(data),
      [`${config.resultsDir}/scenario-plan.json`]: JSON.stringify(
        { plan, t0Ms: setup?.t0Ms ?? null },
        null,
        2,
      ),
    };
  };
}
