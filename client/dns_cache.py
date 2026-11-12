"""
DNS Cache Module for DNS-SDN Resolution System
Provides thread-safe positive and negative caching with independent TTLs,
cache hit/miss statistics, expiration tracking, and size monitoring.
"""

import time
import threading
from typing import Optional, Tuple, Dict, Any


class CacheEntry:
    """Represents a single DNS cache record."""

    def __init__(self, hostname: str, value: Optional[str], is_negative: bool, ttl_seconds: float):
        self.hostname = hostname.lower().strip()
        self.value = value  # IP address or None for NOT_FOUND
        self.is_negative = is_negative
        self.ttl = ttl_seconds
        self.created_at = time.monotonic()
        self.created_wall_time = time.time()
        self.expires_at = self.created_at + ttl_seconds
        self.hits = 0

    @property
    def remaining_ttl(self) -> float:
        """Remaining lifetime in seconds (can be negative if expired)."""
        return max(0.0, self.expires_at - time.monotonic())

    @property
    def is_expired(self) -> bool:
        """Check if entry has outlived its TTL."""
        return time.monotonic() >= self.expires_at


class DNSCache:
    """
    Thread-safe DNS Cache with positive and negative caching,
    configurable TTLs, and real-time statistics.
    """

    def __init__(self, positive_ttl: float = 100.0, negative_ttl: float = 30.0, max_entries: int = 1000):
        self.positive_ttl = float(positive_ttl)
        self.negative_ttl = float(negative_ttl)
        self.max_entries = int(max_entries)

        self._cache: Dict[str, CacheEntry] = {}
        self._lock = threading.Lock()

        # Cumulative statistics
        self.stats = {
            "hits": 0,
            "misses": 0,
            "expirations": 0,
            "evictions": 0,
            "positive_sets": 0,
            "negative_sets": 0
        }

    def get(self, hostname: str) -> Tuple[Optional[str], bool, float]:
        """
        Lookup a hostname in the cache.

        Returns:
            Tuple: (value, is_negative, remaining_ttl)
            - If Cache Hit (Positive): (ip_str, False, remaining_seconds)
            - If Cache Hit (Negative): (None, True, remaining_seconds)
            - If Cache Miss / Expired: (None, False, 0.0)
        """
        normalized_name = hostname.lower().strip()

        with self._lock:
            entry = self._cache.get(normalized_name)

            if entry is None:
                self.stats["misses"] += 1
                return None, False, 0.0

            if entry.is_expired:
                # Expired entry detected
                del self._cache[normalized_name]
                self.stats["expirations"] += 1
                self.stats["misses"] += 1
                return None, False, 0.0

            # Valid Cache Hit
            entry.hits += 1
            self.stats["hits"] += 1
            return entry.value, entry.is_negative, round(entry.remaining_ttl, 2)

    def set(self, hostname: str, ip: str, ttl: Optional[float] = None) -> None:
        """Store a positive resolution result in cache."""
        normalized_name = hostname.lower().strip()
        effective_ttl = float(ttl if ttl is not None else self.positive_ttl)

        with self._lock:
            self._ensure_capacity()
            entry = CacheEntry(
                hostname=normalized_name,
                value=ip.strip(),
                is_negative=False,
                ttl_seconds=effective_ttl
            )
            self._cache[normalized_name] = entry
            self.stats["positive_sets"] += 1

    def set_negative(self, hostname: str, ttl: Optional[float] = None) -> None:
        """Store a negative resolution result (NOT_FOUND) in cache."""
        normalized_name = hostname.lower().strip()
        effective_ttl = float(ttl if ttl is not None else self.negative_ttl)

        with self._lock:
            self._ensure_capacity()
            entry = CacheEntry(
                hostname=normalized_name,
                value=None,
                is_negative=True,
                ttl_seconds=effective_ttl
            )
            self._cache[normalized_name] = entry
            self.stats["negative_sets"] += 1

    def invalidate(self, hostname: Optional[str] = None) -> int:
        """
        Invalidate a single hostname or flush the entire cache.
        Returns the count of entries removed.
        """
        with self._lock:
            if hostname is not None:
                normalized_name = hostname.lower().strip()
                if normalized_name in self._cache:
                    del self._cache[normalized_name]
                    return 1
                return 0
            else:
                count = len(self._cache)
                self._cache.clear()
                return count

    def purge_expired(self) -> int:
        """Manually purge any expired entries and return number purged."""
        purged = 0
        with self._lock:
            keys_to_remove = [k for k, v in self._cache.items() if v.is_expired]
            for k in keys_to_remove:
                del self._cache[k]
                purged += 1
            self.stats["expirations"] += purged
        return purged

    def _ensure_capacity(self) -> None:
        """Evict oldest entry if max_entries is exceeded."""
        if len(self._cache) >= self.max_entries:
            # First purge expired entries
            keys_to_remove = [k for k, v in self._cache.items() if v.is_expired]
            for k in keys_to_remove:
                del self._cache[k]
                self.stats["expirations"] += 1

            # If still full, evict the entry that expires soonest
            if len(self._cache) >= self.max_entries:
                soonest_key = min(self._cache.keys(), key=lambda k: self._cache[k].expires_at)
                del self._cache[soonest_key]
                self.stats["evictions"] += 1

    def get_stats(self) -> Dict[str, Any]:
        """Return cache health, size, and efficiency metrics."""
        with self._lock:
            total_lookups = self.stats["hits"] + self.stats["misses"]
            hit_ratio = (self.stats["hits"] / total_lookups * 100.0) if total_lookups > 0 else 0.0

            positives = sum(1 for e in self._cache.values() if not e.is_negative and not e.is_expired)
            negatives = sum(1 for e in self._cache.values() if e.is_negative and not e.is_expired)

            return {
                "total_lookups": total_lookups,
                "hits": self.stats["hits"],
                "misses": self.stats["misses"],
                "hit_ratio_percent": round(hit_ratio, 2),
                "expirations": self.stats["expirations"],
                "evictions": self.stats["evictions"],
                "active_entries": len(self._cache),
                "positive_entries": positives,
                "negative_entries": negatives,
                "max_entries": self.max_entries,
                "positive_ttl": self.positive_ttl,
                "negative_ttl": self.negative_ttl
            }

    def list_entries(self) -> Dict[str, Dict[str, Any]]:
        """Return snapshot of current valid entries for reporting or UI."""
        with self._lock:
            result = {}
            for k, entry in self._cache.items():
                if not entry.is_expired:
                    result[k] = {
                        "value": entry.value if not entry.is_negative else "NOT_FOUND",
                        "is_negative": entry.is_negative,
                        "remaining_ttl_sec": round(entry.remaining_ttl, 2),
                        "hits": entry.hits
                    }
            return result
