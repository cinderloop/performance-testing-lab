from perflab.ports import port_violations, published_ports


def svc(*ports: dict[str, str]) -> dict[str, object]:
    return {"ports": list(ports)}


def test_loopback_ports_pass() -> None:
    config = {
        "services": {
            "frontend-proxy": svc({"host_ip": "127.0.0.1", "published": "8080", "target": "8080"})
        }
    }
    assert port_violations(config) == []
    assert published_ports(config) == ["127.0.0.1:8080 -> frontend-proxy:8080"]


def test_short_form_port_binds_all_interfaces() -> None:
    # Upstream's `- "5432"` short form resolves to no host_ip, i.e. 0.0.0.0 on a random port.
    config = {"services": {"astronomy-db": svc({"target": "5432"})}}
    (problem,) = port_violations(config)
    assert "astronomy-db" in problem
    assert "0.0.0.0" in problem
    assert "random" in problem


def test_explicit_all_interfaces_and_other_ips_fail() -> None:
    config = {
        "services": {
            "a": svc({"host_ip": "0.0.0.0", "published": "1", "target": "1"}),
            "b": svc({"host_ip": "192.168.1.5", "published": "2", "target": "2"}),
            "c": svc(),
        }
    }
    assert len(port_violations(config)) == 2
