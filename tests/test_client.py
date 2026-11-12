"""
Unit tests for DNS Client (client.py).
Tests end-to-end client resolution, positive/negative caching, timeout handling, and metrics.
"""

import time
import threading
import pytest
from client.client import DNSResolutionClient
from resolver.resolver import UDPResolverServer


def test_client_resolution_workflow(get_free_port):
    port_a = 5000
    port_b = 5001

    srv_a = UDPResolverServer(name="Resolver A", host="127.0.0.1", port=port_a)
    srv_b = UDPResolverServer(name="Resolver B", host="127.0.0.1", port=port_b)

    t_a = threading.Thread(target=srv_a.start, daemon=True)
    t_b = threading.Thread(target=srv_b.start, daemon=True)
    t_a.start()
    t_b.start()
    time.sleep(0.3)

    client = DNSResolutionClient(use_local_ip=True, timeout=1.0)

    try:
        # Query 1: Normal resolution (Cache Miss)
        res1 = client.resolve("server1.local")
        assert res1["status"] == "RESOLVED"
        assert res1["ip"] == "192.0.2.10"
        assert res1["is_cached"] is False
        assert res1["total_time_ms"] > 0

        # Query 2: Repeated query (Cache Hit)
        res2 = client.resolve("server1.local")
        assert res2["status"] == "RESOLVED"
        assert res2["ip"] == "192.0.2.10"
        assert res2["is_cached"] is True
        assert res2["source"] == "CACHE_HIT"

        # Query 3: Non-existent domain (Cache Miss -> NOT_FOUND)
        res3 = client.resolve("invalid.example.corp")
        assert res3["status"] == "NOT_FOUND"
        assert res3["ip"] is None
        assert res3["is_cached"] is False

        # Query 4: Repeated non-existent query (Negative Cache Hit)
        res4 = client.resolve("invalid.example.corp")
        assert res4["status"] == "NOT_FOUND"
        assert res4["is_cached"] is True
        assert "NEGATIVE" in res4["source"]

    finally:
        srv_a.stop()
        srv_b.stop()

