"""
Unit tests for Resolver Selection and Load Balancing (resolver_selector.py).
Tests lowest-latency, round-robin, priority, offline-exclusion, and stale-health handling.
"""

import time
import pytest
from client.resolver_selector import ResolverSelector


def test_lowest_latency_selection():
    selector = ResolverSelector()

    # Mock health data with Resolver B faster than Resolver A
    selector.get_health_data = lambda: ({
        "Resolver A": {"online": True, "latency_ms": 5.4},
        "Resolver B": {"online": True, "latency_ms": 1.2}
    }, True, "Fresh data")

    primary, order, explanation = selector.select_resolver(policy="lowest_latency", use_local_ip=True)
    assert primary["name"] == "Resolver B"
    assert "lowest measured latency" in explanation
    assert order[0]["name"] == "Resolver B"
    assert order[1]["name"] == "Resolver A"


def test_round_robin_selection():
    selector = ResolverSelector()
    selector.get_health_data = lambda: ({
        "Resolver A": {"online": True, "latency_ms": 2.0},
        "Resolver B": {"online": True, "latency_ms": 2.0}
    }, True, "Fresh data")

    p1, _, _ = selector.select_resolver(policy="round_robin", use_local_ip=True)
    p2, _, _ = selector.select_resolver(policy="round_robin", use_local_ip=True)
    p3, _, _ = selector.select_resolver(policy="round_robin", use_local_ip=True)

    # In round-robin, sequential calls alternate between healthy servers
    assert p1["name"] != p2["name"]
    assert p1["name"] == p3["name"]


def test_offline_exclusion():
    selector = ResolverSelector()

    # Resolver A is offline; Resolver B is online
    selector.get_health_data = lambda: ({
        "Resolver A": {"online": False, "latency_ms": None},
        "Resolver B": {"online": True, "latency_ms": 2.5}
    }, True, "Fresh data")

    primary, order, _ = selector.select_resolver(policy="lowest_latency", use_local_ip=True)
    assert primary["name"] == "Resolver B"
    # Unhealthy server placed at the end of failover list
    assert order[-1]["name"] == "Resolver A"


def test_stale_health_fallback():
    selector = ResolverSelector()

    # Health reported as stale
    selector.get_health_data = lambda: ({
        "Resolver A": {"online": True, "latency_ms": 1.0}
    }, False, "Stale data (>15s)")

    primary, order, _ = selector.select_resolver(policy="priority", use_local_ip=True)
    # Under priority, Resolver A is rank 1
    assert primary["name"] == "Resolver A"
