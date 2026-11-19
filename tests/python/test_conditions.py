from datetime import UTC, datetime

from perflab.conditions import (
    Proc,
    busy_processes,
    events_during,
    parse_loadavg,
    parse_power_source,
    parse_powermode,
    parse_processinfo,
    parse_top,
    running_heavy_apps,
)

BATT_AC = "Now drawing from 'AC Power'\n -InternalBattery-0 (id=1)\t100%; charged; present: true\n"
BATT_BATTERY = "Now drawing from 'Battery Power'\n -InternalBattery-0 (id=1)\t19%; discharging\n"

TOP = """Processes: 700 total
PID    %CPU COMMAND
400    90.0 WindowServer
1      0.0  launchd

PID    %CPU COMMAND
43806  5.3  top
500    41.0 com.apple.Virtua
600    33.5 mdworker_shared
700    24.9 Terminal
800    80.0 com.docker.backend
"""


def test_power_source() -> None:
    assert parse_power_source(BATT_AC) == "AC Power"
    assert parse_power_source(BATT_BATTERY) == "Battery Power"
    assert parse_power_source("") is None


def test_powermode() -> None:
    assert parse_powermode(" displaysleep         2\n powermode            0\n") == "0"
    assert parse_powermode("nothing") is None


def test_processinfo() -> None:
    assert parse_processinfo("lpm=false thermal=0\n") == (False, 0)
    assert parse_processinfo("lpm=true thermal=2\n") == (True, 2)
    assert parse_processinfo("swift: command not found") == (None, None)


def test_loadavg() -> None:
    assert parse_loadavg("{ 2.21 4.38 4.23 }\n") == [2.21, 4.38, 4.23]


def test_top_uses_last_sample_only() -> None:
    procs = parse_top(TOP)
    assert [p.pid for p in procs] == [43806, 500, 600, 700, 800]
    assert procs[1] == Proc(500, 41.0, "com.apple.Virtua")


def test_busy_processes_ignores_lab_and_threshold() -> None:
    busy = busy_processes(parse_top(TOP))
    # Docker VM and backend are the lab itself; Terminal is under 25 %; Spotlight counts.
    assert [p.command for p in busy] == ["mdworker_shared"]


def test_heavy_apps() -> None:
    ps = (
        "COMM\n/Applications/Google Chrome.app/Contents/MacOS/Google Chrome\n"
        "/Applications/Transmission.app/Contents/MacOS/Transmission\n/usr/sbin/cfprefsd\n"
    )
    assert running_heavy_apps(ps) == ["Google Chrome", "Transmission"]
    assert running_heavy_apps("COMM\n/usr/libexec/trustd\n") == []


PMSET_LOG = "\n".join(
    [
        "2026-11-20 01:50:00 +0530 Assertions   \tSummary- [System: PrevIdle] Using AC(Charge: 40)",
        "2026-11-20 02:05:14 +0530 Assertions   \tSummary- [System: kCPU] Using Batt(Charge: 37)",
        "2026-11-20 02:05:17 +0530 Sleep        \tEntering Sleep state due to 'Clamshell Sleep'",
        "2026-11-20 02:05:18 +0530 Wake Requests\t[process=dasd request=SleepService]",
        "2026-11-20 02:05:50 +0530 Wake         \tWake from Deep Idle [CDNVA] : due to lid",
        "2026-11-20 03:00:00 +0530 Sleep        \tEntering Sleep state due to 'Idle Sleep'",
    ]
)


def test_power_log_events_within_the_run_window() -> None:
    # 01:55-02:30 +0530 = 20:25-21:00 UTC the day before
    start = datetime(2026, 11, 19, 20, 25, tzinfo=UTC)
    end = datetime(2026, 11, 19, 21, 0, tzinfo=UTC)
    events = events_during(PMSET_LOG, start, end)
    assert len(events) == 3
    assert "Sleep: Entering Sleep state due to 'Clamshell Sleep'" in events[0]
    assert events[1].split(" ", 1)[1].startswith("Wake: Wake from Deep Idle")
    assert events[2] == "power log shows the Mac running on battery during the run"


def test_power_log_quiet_run() -> None:
    start = datetime(2026, 11, 19, 20, 10, tzinfo=UTC)
    end = datetime(2026, 11, 19, 20, 30, tzinfo=UTC)  # 01:40-02:00 +0530: only AC lines
    assert events_during(PMSET_LOG, start, end) == []
