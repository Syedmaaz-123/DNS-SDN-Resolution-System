import pytest
import time
import socket
import threading
from client.client import DNSResolutionClient
from client.dns_cache import DNSCache
from resolver.resolver import UDPResolverServer

@pytest.fixture
def get_free_port():
    def _alloc():
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.bind(('127.0.0.1', 0))
        port = s.getsockname()[1]
        s.close()
        return port
    return _alloc

def test_cache_hit_vs_miss_latency():
    cache = DNSCache(positive_ttl=10.0, negative_ttl=5.0)
    
    # Measure MISS latency
    t0 = time.perf_counter()
    val, is_neg, rem_ttl = cache.get("test.example.com")
    miss_latency_ms = (time.perf_counter() - t0) * 1000
    assert val is None
    assert is_neg is False
    
    # Insert entry
    cache.set("test.example.com", "1.2.3.4", ttl=10.0)
    
    # Measure HIT latency
    t1 = time.perf_counter()
    val_hit, is_neg_hit, rem_ttl_hit = cache.get("test.example.com")
    hit_latency_ms = (time.perf_counter() - t1) * 1000
    assert val_hit == "1.2.3.4"
    assert is_neg_hit is False
    assert rem_ttl_hit > 0
    
    # Memory cache lookup should be strictly sub-millisecond
    assert hit_latency_ms < 1.0

def test_individual_query_timing_metrics(tmp_path, get_free_port):
    records_file = tmp_path / "records.json"
    records_file.write_text('{"speed.local": "192.168.1.100"}')
    
    port_a = get_free_port()
    port_b = get_free_port()
    
    server_a = UDPResolverServer(name="Resolver A", host="127.0.0.1", port=port_a, records_path=str(records_file))
    t_a = threading.Thread(target=server_a.start, daemon=True)
    t_a.start()
    time.sleep(0.15)
    
    config = {
        "client": {"timeout": 1.0, "max_retries": 1, "default_ttl": 60},
        "resolvers": {
            "resolver_a": {"name": "Resolver A", "host": "127.0.0.1", "port": port_a, "priority": 1},
            "resolver_b": {"name": "Resolver B", "host": "127.0.0.1", "port": port_b, "priority": 2}
        },
        "monitoring": {"state_file": str(tmp_path / "health.json")}
    }
    
    try:
        client = DNSResolutionClient(config=config, use_local_ip=True)
        res = client.resolve("speed.local")
        assert res["status"] == "RESOLVED"
        assert res["ip"] == "192.168.1.100"
        assert "response_time_ms" in res
        assert "total_time_ms" in res
        assert res["response_time_ms"] > 0
        assert res["total_time_ms"] >= res["response_time_ms"]
    finally:
        server_a.stop()

def test_resolver_latency_comparison(tmp_path, get_free_port):
    records_file = tmp_path / "records.json"
    records_file.write_text('{"compare.local": "10.0.0.99"}')
    
    port_a = get_free_port()
    port_b = get_free_port()
    
    server_a = UDPResolverServer(name="Resolver A", host="127.0.0.1", port=port_a, records_path=str(records_file))
    server_b = UDPResolverServer(name="Resolver B", host="127.0.0.1", port=port_b, records_path=str(records_file))
    threading.Thread(target=server_a.start, daemon=True).start()
    threading.Thread(target=server_b.start, daemon=True).start()
    time.sleep(0.15)
    
    config = {
        "client": {"timeout": 1.0, "max_retries": 1, "default_ttl": 60},
        "resolvers": {
            "resolver_a": {"name": "Resolver A", "host": "127.0.0.1", "port": port_a, "priority": 1},
            "resolver_b": {"name": "Resolver B", "host": "127.0.0.1", "port": port_b, "priority": 2}
        },
        "monitoring": {"state_file": str(tmp_path / "health.json")}
    }
    
    try:
        client = DNSResolutionClient(config=config, use_local_ip=True)
        res_a = client.resolve("compare.local")
        assert res_a["status"] == "RESOLVED"
        assert res_a["source"] in ("Resolver A", "resolver_a")
        assert res_a["response_time_ms"] < 100.0  # Local UDP typically < 2ms
    finally:
        server_a.stop()
        server_b.stop()

def test_failover_latency_measurement(tmp_path, get_free_port):
    records_file = tmp_path / "records.json"
    records_file.write_text('{"failover.local": "10.0.0.101"}')
    
    dead_port = get_free_port()
    live_port = get_free_port()
    
    server_b = UDPResolverServer(name="Resolver B", host="127.0.0.1", port=live_port, records_path=str(records_file))
    threading.Thread(target=server_b.start, daemon=True).start()
    time.sleep(0.15)
    
    config = {
        "client": {"timeout": 0.2, "max_retries": 0, "default_ttl": 60},
        "resolvers": {
            "resolver_a": {"name": "Resolver A", "host": "127.0.0.1", "port": dead_port, "priority": 1},
            "resolver_b": {"name": "Resolver B", "host": "127.0.0.1", "port": live_port, "priority": 2}
        },
        "monitoring": {"state_file": str(tmp_path / "health.json")}
    }
    
    try:
        client = DNSResolutionClient(config=config, use_local_ip=True)
        t_start = time.perf_counter()
        res = client.resolve("failover.local")
        elapsed_ms = (time.perf_counter() - t_start) * 1000
        
        # Must failover to Resolver B
        assert res["status"] == "RESOLVED"
        assert res["source"] in ("Resolver B", "resolver_b")
        assert res["ip"] == "10.0.0.101"
        assert res["failover_occurred"] is True
        # Total latency should reflect timeout of A (~200ms) + resolution on B (~1ms)
        assert elapsed_ms >= 180.0
    finally:
        server_b.stop()
