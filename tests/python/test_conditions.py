from perflab.conditions import (
    Proc,
    busy_processes,
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
