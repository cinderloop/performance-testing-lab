import math

import pytest

from perflab.reset import (
    check_flags,
    check_gc_gate,
    check_go_memory,
    check_idle_frontend,
    check_kafka,
    check_loadgen,
    check_orders,
    check_valkey,
    parse_envoy_counter,
)

PRISTINE = {
    "flags": {"adFailure": {"defaultVariant": "off"}, "cartFailure": {"defaultVariant": "off"}}
}


def test_orders() -> None:
    assert check_orders("0\n").passed
    assert not check_orders("3\n").passed
    assert not check_orders("").passed


def test_valkey_allows_the_bookkeeping_key() -> None:
    assert check_valkey("1\n").passed
    assert check_valkey("0").passed
    assert not check_valkey("4").passed
    assert not check_valkey("Could not connect").passed


def test_kafka_offsets() -> None:
    assert check_kafka("orders:0:0\n").passed
    assert not check_kafka("orders:0:12\n").passed
    assert not check_kafka("orders:0:0\norders:1:5\n").passed
    assert not check_kafka("Error: topic does not exist").passed


def test_flags() -> None:
    assert check_flags(PRISTINE, PRISTINE).passed
    on = {
        "flags": {"adFailure": {"defaultVariant": "on"}, "cartFailure": {"defaultVariant": "off"}}
    }
    c = check_flags(on, PRISTINE)
    assert not c.passed
    assert c.observed["differs"] == {"adFailure": "on"}
    extra = {"flags": {**PRISTINE["flags"], "newFlag": {"defaultVariant": "off"}}}
    assert not check_flags(extra, PRISTINE).passed
    assert not check_flags({"flags": {"adFailure": {"defaultVariant": "off"}}}, PRISTINE).passed


def test_loadgen() -> None:
    clean = check_loadgen([{"Names": ["/frontend"]}], 503)
    assert all(c.passed for c in clean)
    present = check_loadgen([{"Names": ["/load-generator"]}], 200)
    assert [c.passed for c in present] == [False, False]


def test_envoy_counter() -> None:
    stats = "cluster.frontend.upstream_rq_total: 42\ncluster.frontend.upstream_rq_totalx: 9\n"
    assert parse_envoy_counter(stats) == 42
    with pytest.raises(ValueError, match="not found"):
        parse_envoy_counter("cluster.other.upstream_rq_total: 1\n")


def test_idle_frontend() -> None:
    assert check_idle_frontend(10, 11).passed
    assert check_idle_frontend(10, 12).passed
    assert not check_idle_frontend(10, 13).passed


def test_gc_gate() -> None:
    ok = check_gc_gate({"product-catalog": 0.004, "checkout": 0.05})
    assert all(c.passed for c in ok)
    spiral = check_gc_gate({"product-catalog": 1.0, "checkout": 0.003})
    assert [c.passed for c in spiral] == [False, True]
    missing = check_gc_gate({"checkout": 0.0})
    assert not missing[0].passed
    assert math.isnan(missing[0].observed)


def test_go_memory() -> None:
    limit = 48 * 2**20
    ok = check_go_memory(
        {"product-catalog": 15e6, "checkout": 13e6}, {"product-catalog": limit, "checkout": limit}
    )
    assert all(c.passed for c in ok)
    # Spike §3: 17.2 MB used against the upstream 16 MiB limit is the death-spiral state.
    over = check_go_memory({"product-catalog": 17.2e6}, {"product-catalog": 16 * 2**20})
    assert not over[0].passed
    assert not over[1].passed  # no data for checkout fails closed
