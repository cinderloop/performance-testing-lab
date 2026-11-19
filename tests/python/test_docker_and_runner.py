import re
from datetime import UTC, datetime
from pathlib import Path

import pytest

from perflab.dockerapi import cores_between, parse_sample, parse_time
from perflab.runner import code_changes, k6_command, make_run_id, script_env, service_settings


def stats(read: str, cpu_ns: int, usage: int = 100, inactive: int = 30) -> dict[str, object]:
    return {
        "read": read,
        "cpu_stats": {"cpu_usage": {"total_usage": cpu_ns}, "online_cpus": 16},
        "memory_stats": {"usage": usage, "stats": {"inactive_file": inactive}},
    }


def test_parse_time_keeps_microseconds_of_nanosecond_timestamps() -> None:
    t = parse_time("2026-11-19T19:46:26.347763547Z")
    assert t == datetime(2026, 11, 19, 19, 46, 26, 347763, tzinfo=UTC)


def test_sample_and_cores() -> None:
    a = parse_sample(stats("2026-11-19T10:00:00.000000000Z", 1_000_000_000))
    b = parse_sample(stats("2026-11-19T10:00:30.000000000Z", 1_150_000_000))
    assert a.mem_bytes == 70  # usage minus inactive file cache
    # 0.15 s of CPU over 30 s of wall time = 0.005 cores
    assert cores_between(a, b) == pytest.approx(0.005)
    with pytest.raises(ValueError, match="increasing"):
        cores_between(b, a)


def test_run_id_format() -> None:
    rid = make_run_id("scenarios/foundation-check.ts", datetime(2026, 11, 20, 1, 2, 3, tzinfo=UTC))
    assert re.fullmatch(r"20261120T010203Z-foundation-check-[0-9a-f]{4}", rid)


def test_script_env_defaults_and_overrides() -> None:
    env = script_env("r1", {"TIMEOUT_MS": "2500"})
    assert env == {
        "BASE_URL": "http://frontend-proxy:8080",
        "RUN_ID": "r1",
        "RESULTS_DIR": "/results",
        "TIMEOUT_MS": "2500",
    }


def test_k6_command_always_disables_usage_reporting_and_uses_the_demo_network() -> None:
    cmd = k6_command(
        image="img@sha256:x",
        network="opentelemetry-demo",
        container="k6-r1",
        scenario="scenarios/a.ts",
        results=Path("/tmp/r1"),
        env={"RUN_ID": "r1"},
        k6_args=["--vus", "2"],
    )
    assert cmd[:6] == ["docker", "create", "--name", "k6-r1", "--network", "opentelemetry-demo"]
    assert "K6_NO_USAGE_REPORT=true" in cmd
    assert "--no-usage-report" in cmd
    assert "json=/results/k6-raw.json.gz" in cmd
    run_at = cmd.index("run")
    assert cmd[run_at - 1] == "img@sha256:x"
    assert cmd[cmd.index("-e", run_at) + 1] == "RUN_ID=r1"  # script env via k6's own -e
    assert cmd[-3:] == ["--vus", "2", "/k6/scenarios/a.ts"]


def test_service_settings_reads_limits_sampler_and_intervals() -> None:
    config = {
        "services": {
            "checkout": {
                "deploy": {"resources": {"limits": {"memory": "67108864"}}},
                "environment": {
                    "GOMEMLIMIT": "48MiB",
                    "OTEL_METRIC_EXPORT_INTERVAL": "10000",
                    "OTEL_SERVICE_NAME": "checkout",
                },
            },
            "valkey-cart": {"deploy": {"resources": {"limits": {"memory": "20971520"}}}},
            "jaeger": {"environment": {"MEMORY_MAX_TRACES": "25000"}},
        }
    }
    s = service_settings(config)
    assert s["resource_limits"]["checkout"] == {
        "memory_bytes": 67108864,
        "cpus": None,
        "gomemlimit": "48MiB",
    }
    assert s["tracing"]["sampler"] == {"checkout": "parentbased_always_on (SDK default)"}
    assert s["tracing"]["jaeger_memory_max_traces"] == "25000"
    assert s["metric_intervals"]["sdk_export_interval_ms"] == {"checkout": "10000"}


def test_results_dont_count_as_code_changes() -> None:
    porcelain = (
        "?? results/20261120T000000Z-smoke-abcd/manifest.json\n"
        " M results/README.md\n"
        " M k6/lib/http.ts\n"
        "?? docs/new.md\n"
        '?? "results/with space/x"\n'
    )
    assert code_changes(porcelain) == [" M k6/lib/http.ts", "?? docs/new.md"]
