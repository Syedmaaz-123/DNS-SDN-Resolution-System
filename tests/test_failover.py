"""
Integration tests for Failover and Dynamic Recovery (test_failover.py).
Verifies that failure of Resolver A transparently fails over to Resolver B,
and recovery of Resolver A restores healthy operations without service interruption.
"""

import time
import threading
import pytest
from client.client import DNSResolutionClient
from resolver.resolver import UDPResolverServer
from monitoring.health_monitor import HealthMonitor


def test_automatic_failover_and_recovery():
    # Setup Resolver A on port 5000 and Resolver B on port 5001
    srv_a = UDPResolverServer(name="Resolver A", host="127.0.0.1", port=5000)
    srv_b = UDPResolverServer(name="Resolver B", host="127.0.0.1", port=5001)

    t_a = threading.Thread(target=srv_a.start, daemon=True)
    t_b = threading.Thread(target=srv_b.start, daemon=True)
    t_a.start()
    t_b.start()
    time.sleep(0.3)

    client = DNSResolutionClient(use_local_ip=True, timeout=0.8)

    try:
        # Phase 1: Normal operation (Resolver A active)
        client.cache.invalidate()
        res1 = client.resolve("server1.local", override_policy="priority")
        assert res1["status"] == "RESOLVED"
        assert res1["source"] == "Resolver A"
        assert res1["failover_occurred"] is False

        # Phase 2: Simulate Resolver A failure by shutting it down
        srv_a.stop()
        time.sleep(0.3)

        # Query again: Client must detect Resolver A timeout and failover to Resolver B!
        client.cache.invalidate()
        res2 = client.resolve("server1.local", override_policy="priority")
        assert res2["status"] == "RESOLVED"
        assert res2["source"] == "Resolver B"
        assert res2["failover_occurred"] is True
        print(f"\n[VERIFIED] Failover succeeded to {res2['source']} in {res2['total_time_ms']} ms")

        # Phase 3: Resolver A recovers (Restart Resolver A)
        srv_a_recovered = UDPResolverServer(name="Resolver A", host="127.0.0.1", port=5000)
        t_a_rec = threading.Thread(target=srv_a_recovered.start, daemon=True)
        t_a_rec.start()
        time.sleep(0.3)

        # Query again: Resolver A is back online and handles the request
        client.cache.invalidate()
        res3 = client.resolve("server1.local", override_policy="priority")
        assert res3["status"] == "RESOLVED"
        assert res3["source"] == "Resolver A"
        assert res3["failover_occurred"] is False
        print(f"[VERIFIED] Recovery succeeded. Request handled by {res3['source']}")

        srv_a_recovered.stop()

    finally:
        srv_b.stop()

