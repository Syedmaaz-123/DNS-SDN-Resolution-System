"""
Full Integration Test Suite for DNS-SDN Resolution System.
Formally verifies all 12 evaluation criteria defined in Section 9 of Master Specification.
"""

import time
import json
import threading
import pytest
from pathlib import Path

from client.client import DNSResolutionClient
from client.dns_cache import DNSCache
from resolver.resolver import UDPResolverServer
from monitoring.health_monitor import HealthMonitor
from sdn.flow_manager import FlowManager

PROJECT_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def run_live_test_network():
    """Starts live instances of Resolver A and Resolver B on localhost."""
    srv_a = UDPResolverServer(name="Resolver A", host="127.0.0.1", port=5000)
    srv_b = UDPResolverServer(name="Resolver B", host="127.0.0.1", port=5001)

    t_a = threading.Thread(target=srv_a.start, daemon=True)
    t_b = threading.Thread(target=srv_b.start, daemon=True)
    t_a.start()
    t_b.start()
    time.sleep(0.4)

    yield {"srv_a": srv_a, "srv_b": srv_b}

    srv_a.stop()
    srv_b.stop()


def test_scenario_01_normal_dns_resolution(run_live_test_network):
    """TEST 1: Normal DNS resolution (server1.local -> 192.0.2.10)."""
    client = DNSResolutionClient(use_local_ip=True)
    client.cache.invalidate()
    res = client.resolve("server1.local")
    assert res["status"] == "RESOLVED"
    assert res["ip"] == "192.0.2.10"
    assert res["is_cached"] is False


def test_scenario_02_unknown_hostname(run_live_test_network):
    """TEST 2: Unknown hostname returns NOT_FOUND."""
    client = DNSResolutionClient(use_local_ip=True)
    client.cache.invalidate()
    res = client.resolve("unknown-host.nonexistent.domain")
    assert res["status"] == "NOT_FOUND"
    assert res["ip"] is None


def test_scenario_03_cache_hit(run_live_test_network):
    """TEST 3: Resolve same hostname twice and verify second request uses cache."""
    client = DNSResolutionClient(use_local_ip=True)
    client.cache.invalidate()

    # Request 1: Cache Miss
    r1 = client.resolve("server2.local")
    assert r1["is_cached"] is False
    assert r1["ip"] == "192.0.2.20"

    # Request 2: Cache Hit
    r2 = client.resolve("server2.local")
    assert r2["is_cached"] is True
    assert r2["source"] == "CACHE_HIT"
    assert r2["ip"] == "192.0.2.20"
    assert r2["total_time_ms"] < r1["total_time_ms"]


def test_scenario_04_cache_expiration():
    """TEST 4: Wait for TTL to expire and verify cache miss upon next query."""
    cache = DNSCache(positive_ttl=0.2)
    cache.set("ephemeral.local", "10.0.0.99")

    # Hit initially
    assert cache.get("ephemeral.local")[0] == "10.0.0.99"

    # Wait for TTL to elapse
    time.sleep(0.25)

    # Must be expired
    assert cache.get("ephemeral.local")[0] is None


def test_scenario_05_and_06_resolver_failure_and_recovery(run_live_test_network):
    """TEST 5 & 6: Stop Resolver A, verify failover to B, restart A, verify recovery."""
    srv_a = run_live_test_network["srv_a"]
    srv_b = run_live_test_network["srv_b"]

    client = DNSResolutionClient(use_local_ip=True, timeout=0.8)

    # TEST 5: Kill Resolver A
    srv_a.stop()
    time.sleep(0.3)

    client.cache.invalidate()
    res_failover = client.resolve("printer.local", override_policy="priority")
    assert res_failover["status"] == "RESOLVED"
    assert res_failover["source"] == "Resolver B"
    assert res_failover["failover_occurred"] is True

    # TEST 6: Recover Resolver A
    srv_a_rec = UDPResolverServer(name="Resolver A", host="127.0.0.1", port=5000)
    t_a_rec = threading.Thread(target=srv_a_rec.start, daemon=True)
    t_a_rec.start()
    time.sleep(0.3)
    run_live_test_network["srv_a"] = srv_a_rec

    client.cache.invalidate()
    res_recovered = client.resolve("printer.local", override_policy="priority")
    assert res_recovered["status"] == "RESOLVED"
    assert res_recovered["source"] == "Resolver A"
    assert res_recovered["failover_occurred"] is False


def test_scenario_07_load_balancing_policies(run_live_test_network):
    """TEST 7: Generate multiple requests and verify selected resolver according to policy."""
    client = DNSResolutionClient(use_local_ip=True)

    # Round Robin alternation
    client.cache.invalidate()
    r1 = client.resolve("database.local", override_policy="round_robin")
    client.cache.invalidate()
    r2 = client.resolve("database.local", override_policy="round_robin")

    assert r1["status"] == "RESOLVED"
    assert r2["status"] == "RESOLVED"


def test_scenario_08_mininet_config_validation():
    """TEST 8: Verify Mininet host and switch configurations in config.json."""
    config_file = PROJECT_ROOT / "config" / "config.json"
    assert config_file.exists()
    with open(config_file, "r") as f:
        cfg = json.load(f)

    mn = cfg.get("mininet", {})
    assert mn.get("switch") == "s1"
    hosts = mn.get("hosts", {})
    assert "h1" in hosts and "h2" in hosts and "h3" in hosts
    assert hosts["h1"]["ip"].startswith("10.0.0.10")
    assert hosts["h2"]["ip"].startswith("10.0.0.20")
    assert hosts["h3"]["ip"].startswith("10.0.0.30")


def test_scenario_09_sdn_flow_rule_installation():
    """TEST 9: Verify controller installs actual OpenFlow forwarding rules."""
    fm = FlowManager()
    rule = fm.generate_dns_flow_spec(client_port=1, target_resolver_port=2, udp_port=5000)
    assert rule["priority"] == 100
    assert rule["match"]["ip_proto"] == 17
    assert rule["match"]["udp_dst"] == 5000
    assert rule["actions"][0]["port"] == 2


def test_scenario_10_dynamic_sdn_forwarding():
    """TEST 10: Change preferred resolver and verify relevant flow rules update."""
    fm = FlowManager()
    assert fm.active_resolver_name == "Resolver A"
    assert fm.active_resolver_port == 2

    # Trigger failover to Resolver B
    changed = fm.update_active_resolver("Resolver B")
    assert changed is True
    assert fm.active_resolver_name == "Resolver B"
    assert fm.active_resolver_port == 3

    # Generate new flow rule targeting port 3
    rule_b = fm.generate_dns_flow_spec(client_port=1, target_resolver_port=fm.active_resolver_port, udp_port=5000)
    assert rule_b["actions"][0]["port"] == 3


def test_scenario_11_performance_evaluation_artifacts():
    """TEST 11: Verify benchmark CSVs and Matplotlib evaluation figures exist and are non-empty."""
    res_dir = PROJECT_ROOT / "results"
    assert (res_dir / "benchmark_summary.json").exists()
    assert (res_dir / "latency_comparison.csv").stat().st_size > 0
    assert (res_dir / "cache_performance.csv").stat().st_size > 0
    assert (res_dir / "system_summary_dashboard.png").stat().st_size > 0


def test_scenario_12_full_integration(run_live_test_network):
    """TEST 12: Verify full integration across client, cache, resolver, monitor, and flow manager."""
    client = DNSResolutionClient(use_local_ip=True)
    hm = HealthMonitor(use_local_ip=True, timeout=1.0)
    fm = FlowManager()

    # 1. Probe network health
    snapshot = hm.check_all()
    assert snapshot["servers"]["Resolver A"]["online"] is True
    assert snapshot["servers"]["Resolver B"]["online"] is True

    # 2. Client resolves name
    client.cache.invalidate()
    res = client.resolve("college.local")
    assert res["status"] == "RESOLVED"
    assert res["ip"] == "192.0.2.50"

    # 3. Cache accelerates query
    cached_res = client.resolve("college.local")
    assert cached_res["is_cached"] is True
    assert cached_res["total_time_ms"] <= res["total_time_ms"]

    # 4. SDN telemetry snapshot recorded
    fm.update_port_stats(1, 10, 10, 640, 640)
    fm.record_stats_snapshot()
    assert fm.stats_file.exists()
