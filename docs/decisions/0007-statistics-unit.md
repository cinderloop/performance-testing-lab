# ADR 0007: The run is the unit for comparing configurations

- Status: **Accepted** (2026-11-20, Phase 1). Methods are fixed here; Phase 4.7 measures their power on this setup.
- Evidence: [spike-findings.md §14](../spike-findings.md#14-baseline-run-to-run-noise-spike-only-invalid-conditions)

## Context

Requests within one run aren't independent samples. They share the run's start state, JIT and cache warm-up, background activity on the laptop, thermal state, and in a closed model they queue behind each other. Treating 50,000 requests as 50,000 independent observations makes confidence intervals far too narrow, and almost any difference looks "significant".

The spike showed this concretely. Across five short runs, medians varied 2–12% but per-run p95 varied up to 55%, and for checkout the pooled p95 differed from the mean of per-run p95s by almost 2×.

## Decision

1. **Comparing two configurations:**
   - Run each **at least 5 times**, each after the reset protocol, interleaved (A B A B …) where practical so slow drift affects both.
   - Compute one statistic per run (for example the success-only p95 per endpoint group, from that run's raw data, excluding warm-up).
   - The runs are the samples.
2. **Interval:** a percentile **bootstrap over runs** (resample runs with replacement within each configuration, 10,000 resamples) for the difference in the per-run statistic, with a 95% interval.
3. **Test:** an **exact permutation test** on the per-run statistic (difference of means). With 5 + 5 runs that's all 252 relabellings. Mann–Whitney U is reported alongside as the conventional non-parametric test. With n = 5 per side its smallest possible two-sided p is 0.008, which is the floor of what this design can show.
4. **Describing one configuration's latency distribution:** percentiles from the **pooled raw data of all its runs**, never the average of per-run percentiles. Both are shown when the difference is itself the point (Phase 4.3).
5. **Block bootstrap over time windows** is allowed only where a single long run is the object of study (the soak test, warm-up). The block length must exceed the autocorrelation time of the windowed statistic, and the experiment doc justifies it.
6. Every comparison states the **minimum detectable difference** for its run count, measured in Phase 4.7, not assumed.

## Consequences

- Five runs give little power. Small differences will be reported as "not distinguishable on this setup", and that's a valid result.
- Experiments get longer runs instead of more requests per second, because a stable per-run p95 needs enough samples (spike: about 44 samples per endpoint gave a p95 CV up to 55%).
- Analysis code implements exactly these methods, with unit tests using hand-computed values (Phase 4).
