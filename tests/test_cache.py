"""
Unit tests for DNS Caching module (dns_cache.py).
Tests positive caching, negative caching, expiration, statistics, and eviction.
"""

import time
import pytest
from client.dns_cache import DNSCache


def test_positive_caching_and_hit():
    cache = DNSCache(positive_ttl=10.0, negative_ttl=5.0)

    # Initial state: Miss
    val, is_neg, ttl = cache.get("server1.local")
    assert val is None
    assert not is_neg
    assert ttl == 0.0

    # Store entry
    cache.set("server1.local", "192.0.2.10")

    # Immediate lookup: Hit
    val2, is_neg2, ttl2 = cache.get("server1.local")
    assert val2 == "192.0.2.10"
    assert not is_neg2
    assert 0 < ttl2 <= 10.0

    stats = cache.get_stats()
    assert stats["hits"] == 1
    assert stats["misses"] == 1
    assert stats["positive_entries"] == 1


def test_negative_caching_and_hit():
    cache = DNSCache(positive_ttl=10.0, negative_ttl=5.0)

    # Cache negative entry (NOT_FOUND)
    cache.set_negative("nonexistent.local")

    val, is_neg, ttl = cache.get("nonexistent.local")
    assert val is None
    assert is_neg is True
    assert 0 < ttl <= 5.0

    stats = cache.get_stats()
    assert stats["hits"] == 1
    assert stats["negative_entries"] == 1


def test_cache_expiration():
    # Cache with ultra-short TTL (0.1s)
    cache = DNSCache(positive_ttl=0.1, negative_ttl=0.1)
    cache.set("shortlife.local", "192.0.2.99")

    # Valid immediately
    val, _, _ = cache.get("shortlife.local")
    assert val == "192.0.2.99"

    # Wait for expiration
    time.sleep(0.15)

    # Must be expired and return None
    val_after, is_neg, _ = cache.get("shortlife.local")
    assert val_after is None
    assert is_neg is False

    stats = cache.get_stats()
    assert stats["expirations"] >= 1


def test_cache_invalidation():
    cache = DNSCache(positive_ttl=10.0)
    cache.set("a.local", "1.1.1.1")
    cache.set("b.local", "2.2.2.2")

    assert cache.get("a.local")[0] == "1.1.1.1"

    # Invalidate single entry
    removed = cache.invalidate("a.local")
    assert removed == 1
    assert cache.get("a.local")[0] is None
    assert cache.get("b.local")[0] == "2.2.2.2"

    # Flush all
    all_removed = cache.invalidate()
    assert all_removed == 1
    assert cache.get("b.local")[0] is None


def test_cache_capacity_and_eviction():
    # Max entries = 3
    cache = DNSCache(positive_ttl=50.0, max_entries=3)
    cache.set("h1.local", "10.0.0.1")
    cache.set("h2.local", "10.0.0.2")
    cache.set("h3.local", "10.0.0.3")

    assert cache.get_stats()["active_entries"] == 3

    # Add 4th entry - triggers eviction
    cache.set("h4.local", "10.0.0.4")
    stats = cache.get_stats()
    assert stats["active_entries"] <= 3
    assert stats["evictions"] >= 1
