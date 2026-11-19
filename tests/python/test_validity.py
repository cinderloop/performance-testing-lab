from dataclasses import replace

from perflab.conditions import Conditions, Proc
from perflab.validity import RunFacts, invalid_reasons, summarize

GOOD_CONDITIONS = Conditions(
    power_source="AC Power",
    low_power_mode=False,
    thermal_state=0,
    pmset_therm="Note: No thermal warning level has been recorded",
    powermode="0",
    load_average=[1.0, 1.0, 1.0],
    top_processes=[Proc(1, 60.0, "com.apple.Virtua")],
)

GOOD = RunFacts(
    reset_ran=True,
    reset_failures=[],
    loadgen_off=True,
    conditions_before=GOOD_CONDITIONS,
    conditions_after=GOOD_CONDITIONS,
    other_containers=[],
    git_dirty_files=[],
    digest_mismatches=[],
    docker_memory_bytes=12_479_537_152,
    usage_report_disabled=True,
    display_sleep_prevented=True,
)


def test_all_conditions_met_is_valid() -> None:
    assert invalid_reasons(GOOD) == []
    assert summarize([]) == {"valid": True, "invalid_reasons": []}


def test_each_rule_makes_the_run_invalid() -> None:
    battery = replace(GOOD_CONDITIONS, power_source="Battery Power")
    cases = {
        "reset protocol did not run": replace(GOOD, reset_ran=False),
        "reset check failed": replace(GOOD, reset_failures=["orders_empty: observed '3'"]),
        "load generator": replace(GOOD, loadgen_off=False),
        "not on mains power": replace(GOOD, conditions_after=battery),
        "Low Power Mode is on": replace(
            GOOD, conditions_before=replace(GOOD_CONDITIONS, low_power_mode=True)
        ),
        "Low Power Mode is unknown": replace(
            GOOD, conditions_before=replace(GOOD_CONDITIONS, low_power_mode=None)
        ),
        "thermal state not nominal (1)": replace(
            GOOD, conditions_after=replace(GOOD_CONDITIONS, thermal_state=1)
        ),
        "heavy applications running: Transmission": replace(
            GOOD, conditions_before=replace(GOOD_CONDITIONS, heavy_apps_running=["Transmission"])
        ),
        "busy non-lab processes: mdworker_shared 40%": replace(
            GOOD,
            conditions_before=replace(
                GOOD_CONDITIONS, top_processes=[Proc(2, 40.0, "mdworker_shared")]
            ),
        ),
        "laptop conditions were not captured": replace(GOOD, conditions_after=None),
        "other containers running: toolshop-worker": replace(
            GOOD, other_containers=["toolshop-worker"]
        ),
        "uncommitted changes": replace(GOOD, git_dirty_files=[" M k6/lib/http.ts"]),
        "image digest mismatch": replace(GOOD, digest_mismatches=["cart: expected sha256:a"]),
        "below the 12 GB minimum": replace(GOOD, docker_memory_bytes=8_321_499_136),
        "usage reporting": replace(GOOD, usage_report_disabled=False),
        "caffeinate": replace(GOOD, display_sleep_prevented=False),
        "during the run: 2026-11-20T02:05:17+05:30 Sleep": replace(
            GOOD, events_during_run=["2026-11-20T02:05:17+05:30 Sleep: Entering Sleep state"]
        ),
    }
    for expected, facts in cases.items():
        reasons = invalid_reasons(facts)
        assert len(reasons) == 1, (expected, reasons)
        assert expected in reasons[0], (expected, reasons)
        assert summarize(reasons)["valid"] is False


def test_before_and_after_are_both_reported() -> None:
    battery = replace(GOOD_CONDITIONS, power_source="Battery Power")
    reasons = invalid_reasons(replace(GOOD, conditions_before=battery, conditions_after=battery))
    assert [r.split(":")[0] for r in reasons] == ["before", "after"]
