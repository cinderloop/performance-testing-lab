/**
 * Load shapes declared once, as named phases. The same declaration produces the k6
 * `ramping-arrival-rate` stages *and* the `scenario-plan.json` file that analysis uses to find
 * "baseline", "recovery" and so on, so the two can't drift apart.
 *
 * Rates are sessions (journey iterations) per minute: arrival-rate executors need whole numbers
 * per time unit, and per-minute gives fine enough steps at laptop scale.
 */

export interface Phase {
  /** e.g. "baseline", "step_2", "spike", "recovery". Unique within a scenario. */
  name: string;
  durationS: number;
  /** Arrival rate at the END of the phase. k6 ramps linearly from the previous phase's rate. */
  targetPerMin: number;
}

export interface PlannedPhase extends Phase {
  startS: number;
  endS: number;
  startPerMin: number;
}

export interface ScenarioPlan {
  scenario: string;
  executor: string;
  rateUnit: "sessions_per_minute";
  phases: PlannedPhase[];
  totalS: number;
}

export function plan(
  scenario: string,
  executor: string,
  startPerMin: number,
  phases: readonly Phase[],
): ScenarioPlan {
  const names = new Set<string>();
  let t = 0;
  let prev = startPerMin;
  const planned: PlannedPhase[] = [];
  for (const p of phases) {
    if (names.has(p.name)) {
      throw new Error(`duplicate phase name ${p.name}`);
    }
    if (!(p.durationS > 0) || p.targetPerMin < 0 || !Number.isInteger(p.targetPerMin)) {
      throw new Error(`phase ${p.name}: duration must be > 0 and rate a whole number >= 0`);
    }
    names.add(p.name);
    planned.push({ ...p, startS: t, endS: t + p.durationS, startPerMin: prev });
    t += p.durationS;
    prev = p.targetPerMin;
  }
  return { scenario, executor, rateUnit: "sessions_per_minute", phases: planned, totalS: t };
}

export function stages(p: ScenarioPlan): { duration: string; target: number }[] {
  return p.phases.map((ph) => ({ duration: `${ph.durationS}s`, target: ph.targetPerMin }));
}

export function peakPerMin(p: ScenarioPlan): number {
  return Math.max(...p.phases.map((ph) => Math.max(ph.startPerMin, ph.targetPerMin)));
}

/**
 * VUs needed for an open model, by Little's Law: concurrency = arrival rate × time in system.
 * `sessionS` is a generous estimate of one session's duration; `headroom` covers slow responses.
 */
export function vusFor(perMin: number, sessionS: number, headroom = 2): number {
  return Math.max(1, Math.ceil((perMin / 60) * sessionS * headroom));
}
