/**
 * Load levels, in sessions per minute (docs/workload-model.md, "Load levels").
 *
 * BREAKPOINT_PER_MIN is MEASURED by the breakpoint scenario on this machine (see the run it
 * comes from in docs/scenarios.md). Every other level is a stated fraction of it. On another
 * machine, run the breakpoint scenario first and update this one number.
 */

/** Highest arrival rate the baseline sustained in the breakpoint run. PLACEHOLDER until measured. */
export const BREAKPOINT_PER_MIN = 600;

/** ASSUMPTION: "normal" load = 40% of the breakpoint, i.e. a system running with 2.5× headroom. */
export const LOAD_PER_MIN = Math.round(BREAKPOINT_PER_MIN * 0.4);
