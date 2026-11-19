# Notes on this run (added 2026-11-20, after the run; manifest.json is unchanged)

**Invalid for comparison.** The manifest flags battery power after the run. Reading the macOS power
log afterwards (`pmset -g log`) shows more:

- 02:05:14 +0530: the Mac was already on battery.
- 02:05:17 +0530: "Entering Sleep state due to 'Clamshell Sleep' … Using Batt (Charge:37%) 33 secs".
  The lid was closed on battery, which `caffeinate` cannot prevent.
- 02:05:50 +0530: wake.

That 33 s sleep froze the whole Docker VM, k6 included. It shows in report.json as a stall around
720–750 s into the run: window p95 of 7.8 s, a throughput dip, and one `api_recommendations` request
"succeeding" after 31.4 s, which is longer than the 10 s request timeout. k6 itself was frozen and
measured wall time on waking.

Because of this, the runner now reads the power log for every run's time window and marks the run
invalid on any sleep, wake or battery use during it (`perflab.conditions.events_during`).

What the run still shows, with the caveat above: the thresholds held up to the end of the ramp
(3000 sessions/min). 500 errors on product-catalog-backed endpoints began in the last few minutes,
so the next breakpoint run ramps to 6000 sessions/min.
