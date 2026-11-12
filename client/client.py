"""
DNS Client Module for DNS-SDN Resolution System
Handles user resolution requests, client-side positive/negative caching,
intelligent resolver selection, automatic failover, and latency measurement.
"""

import sys
import os
import time
import socket
import logging
import argparse
from pathlib import Path
from typing import Optional, Dict, Any, Tuple

# Enable relative and package imports
CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from client.dns_cache import DNSCache
from client.resolver_selector import ResolverSelector

# Configure logging
LOG_DIR = PROJECT_ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "client.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("DNSClient")
# Suppress raw library noise from console if needed, keep console crisp
logger.propagate = False


class DNSResolutionClient:
    """
    High-performance, fault-tolerant DNS-like client with caching,
    intelligent resolver ranking, and automatic failover.
    """

    def __init__(
        self,
        config_path: Optional[str] = None,
        use_local_ip: bool = False,
        policy: Optional[str] = None,
        timeout: float = 2.0,
        config: Optional[Dict[str, Any]] = None
    ):
        self.config_path = config_path or str(PROJECT_ROOT / "config" / "config.json")
        self.selector = ResolverSelector(config=config, config_path=self.config_path)
        self.use_local_ip = use_local_ip
        self.policy = policy or self.selector.default_policy
        self.timeout = timeout

        # Initialize Cache using config settings
        cache_conf = self.selector.config.get("cache", {})
        pos_ttl = float(cache_conf.get("positive_ttl_sec", 100.0))
        neg_ttl = float(cache_conf.get("negative_ttl_sec", 30.0))
        max_ent = int(cache_conf.get("max_entries", 1000))

        self.cache = DNSCache(positive_ttl=pos_ttl, negative_ttl=neg_ttl, max_entries=max_ent)

        # Performance history
        self.query_history = []

    def resolve(self, hostname: str, override_policy: Optional[str] = None) -> Dict[str, Any]:
        """
        Execute full resolution workflow for a hostname:
        1. Check DNS cache (positive & negative)
        2. If cache miss, select best resolver via policy
        3. Send UDP query
        4. On failure, failover to subsequent resolvers
        5. Update cache and return structured result

        Returns:
            Dict containing:
                - hostname: str
                - status: 'RESOLVED', 'NOT_FOUND', or 'FAILED'
                - ip: Optional[str]
                - source: 'CACHE_HIT' or resolver name
                - response_time_ms: float
                - total_time_ms: float
                - is_cached: bool
                - failover_occurred: bool
                - attempts: list of attempted servers
        """
        norm_host = hostname.strip().lower()
        if not norm_host:
            return {
                "hostname": "",
                "status": "FAILED",
                "ip": None,
                "error": "Empty hostname",
                "source": None,
                "response_time_ms": 0.0,
                "total_time_ms": 0.0,
                "is_cached": False,
                "failover_occurred": False,
                "attempts": []
            }

        total_start = time.perf_counter()

        # Step 1: Check Cache
        cached_val, is_neg, remaining_ttl = self.cache.get(norm_host)
        if cached_val is not None:
            # Positive Cache Hit
            total_time = (time.perf_counter() - total_start) * 1000
            result = {
                "hostname": norm_host,
                "status": "RESOLVED",
                "ip": cached_val,
                "source": "CACHE_HIT",
                "response_time_ms": 0.02,
                "total_time_ms": round(total_time, 3),
                "is_cached": True,
                "remaining_ttl_sec": remaining_ttl,
                "failover_occurred": False,
                "attempts": []
            }
            self.query_history.append(result)
            return result

        if is_neg:
            # Negative Cache Hit (cached NOT_FOUND)
            total_time = (time.perf_counter() - total_start) * 1000
            result = {
                "hostname": norm_host,
                "status": "NOT_FOUND",
                "ip": None,
                "source": "CACHE_HIT (NEGATIVE)",
                "response_time_ms": 0.02,
                "total_time_ms": round(total_time, 3),
                "is_cached": True,
                "remaining_ttl_sec": remaining_ttl,
                "failover_occurred": False,
                "attempts": []
            }
            self.query_history.append(result)
            return result

        # Step 2: Cache Miss - Consult Selector
        active_policy = override_policy or self.policy
        primary_server, fallback_order, explanation = self.selector.select_resolver(
            policy=active_policy,
            use_local_ip=self.use_local_ip
        )

        request_packet = f"RESOLVE {norm_host}".encode("utf-8")
        attempts = []
        resolved_ip = None
        final_status = "FAILED"
        winning_server = None
        server_latency = 0.0
        failover_occurred = False

        # Step 3: Iterate through resolvers in prioritized order
        for idx, server in enumerate(fallback_order):
            s_name = server["name"]
            s_ip = server["ip"]
            s_port = server["port"]

            if idx > 0 and not failover_occurred:
                failover_occurred = True

            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(self.timeout)

            attempt_info = {
                "server": s_name,
                "target": f"{s_ip}:{s_port}",
                "status": "PENDING"
            }

            try:
                start_query = time.perf_counter()
                sock.sendto(request_packet, (s_ip, s_port))
                raw_data, _ = sock.recvfrom(1024)
                latency = (time.perf_counter() - start_query) * 1000
                server_latency = round(latency, 3)

                response_text = raw_data.decode("utf-8").strip()
                attempt_info["response"] = response_text
                attempt_info["latency_ms"] = server_latency

                if response_text.startswith("OK "):
                    resolved_ip = response_text[3:].strip()
                    final_status = "RESOLVED"
                    winning_server = s_name
                    attempt_info["status"] = "SUCCESS"
                    attempts.append(attempt_info)

                    # Update positive cache
                    self.cache.set(norm_host, resolved_ip)
                    break

                elif response_text == "NOT_FOUND":
                    final_status = "NOT_FOUND"
                    winning_server = s_name
                    attempt_info["status"] = "NOT_FOUND"
                    attempts.append(attempt_info)

                    # Update negative cache
                    self.cache.set_negative(norm_host)
                    break

                else:
                    attempt_info["status"] = f"PROTOCOL_ERROR: {response_text}"
                    attempts.append(attempt_info)

            except socket.timeout:
                attempt_info["status"] = "TIMEOUT"
                attempts.append(attempt_info)
                logger.warning("Query to %s (%s:%d) timed out. Trying next resolver...", s_name, s_ip, s_port)

            except OSError as err:
                attempt_info["status"] = f"SOCKET_ERROR: {err}"
                attempts.append(attempt_info)
                logger.warning("Query to %s failed: %s. Trying next resolver...", s_name, err)

            finally:
                sock.close()

        total_time = (time.perf_counter() - total_start) * 1000

        result = {
            "hostname": norm_host,
            "status": final_status,
            "ip": resolved_ip,
            "source": winning_server,
            "response_time_ms": server_latency,
            "total_time_ms": round(total_time, 3),
            "is_cached": False,
            "failover_occurred": failover_occurred,
            "attempts": attempts,
            "explanation": explanation
        }
        self.query_history.append(result)
        return result


def run_interactive_client(client: DNSResolutionClient) -> None:
    """Original interactive command-line interface with enhanced visual output."""
    print("=" * 60)
    print("       DNS-SDN INTELLIGENT RESOLUTION CLIENT (v2.0)")
    print("=" * 60)
    print(f"Active Load-Balancing Policy: {client.policy}")
    print(f"Positive Cache TTL: {client.cache.positive_ttl}s | Negative Cache TTL: {client.cache.negative_ttl}s")
    print("Type a hostname (e.g., 'server1.local') or commands:")
    print("  'stats'   -> view cache and query stats")
    print("  'flush'   -> clear DNS cache")
    print("  'policy'  -> toggle policy (lowest_latency / round_robin / priority)")
    print("  'exit'    -> quit")
    print("=" * 60)

    while True:
        try:
            line = input("\nEnter hostname (or 'exit' to quit): ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting client.")
            break

        if not line:
            continue

        cmd = line.lower()
        if cmd == "exit":
            print("Client terminated.")
            break

        if cmd == "stats":
            stats = client.cache.get_stats()
            print("\n--- CACHE & PERFORMANCE STATISTICS ---")
            for k, v in stats.items():
                print(f"  {k}: {v}")
            print(f"  total_queries_in_session: {len(client.query_history)}")
            continue

        if cmd == "flush":
            flushed = client.cache.invalidate()
            print(f"\n[CACHE FLUSHED] Cleared {flushed} cached entries.")
            continue

        if cmd == "policy":
            policies = ["lowest_latency", "round_robin", "priority"]
            current_idx = policies.index(client.policy) if client.policy in policies else 0
            client.policy = policies[(current_idx + 1) % len(policies)]
            print(f"\n[POLICY UPDATED] Active policy is now: '{client.policy}'")
            continue

        # Execute resolution
        res = client.resolve(line)

        if res["is_cached"]:
            if res["status"] == "RESOLVED":
                print(f"\n[CACHE HIT] Valid for {res.get('remaining_ttl_sec', 0):.2f} seconds")
                print("Hostname:", res["hostname"])
                print("IP Address:", res["ip"])
            else:
                print(f"\n[NEGATIVE CACHE HIT] Hostname known not to exist (TTL remaining: {res.get('remaining_ttl_sec', 0):.2f}s)")
                print("Hostname does not exist.")
        else:
            print("\n[CACHE MISS]")
            if res.get("explanation"):
                print(f"[SELECTOR] {res['explanation']}")

            for att in res["attempts"]:
                status_str = att.get("status", "")
                lat = att.get("latency_ms", "N/A")
                if status_str == "TIMEOUT":
                    print(f"  ❌ Tried {att['server']} ({att['target']}) -> TIMEOUT! (Triggering automatic failover...)")
                elif status_str == "SUCCESS":
                    print(f"  ✅ Tried {att['server']} ({att['target']}) -> SUCCESS ({lat} ms)")
                else:
                    print(f"  Tried {att['server']} ({att['target']}) -> {status_str} ({lat} ms)")

            if res.get("failover_occurred"):
                print("\n🚨 [FAILOVER ALERT] Primary resolver failed. Transparently redirected to backup resolver!")

            if res["status"] == "RESOLVED":
                print(f"\nResolved using {res['source']}")
                print("Resolved IP:", res["ip"])
                print(f"Cached for {client.cache.positive_ttl} seconds.")
            elif res["status"] == "NOT_FOUND":
                print(f"\nResolved using {res['source']}")
                print("Hostname does not exist.")
                print(f"Cached negative entry for {client.cache.negative_ttl} seconds.")
            else:
                print("\nERROR: All resolvers unavailable or request failed.")

        print(f"Response time: {res['response_time_ms']:.3f} ms")
        print(f"Total lookup time: {res['total_time_ms']:.3f} ms")


def main():
    parser = argparse.ArgumentParser(description="DNS-SDN Intelligent Resolution Client")
    parser.add_argument("--hostname", "-q", help="Single hostname to resolve directly")
    parser.add_argument("--policy", "-p", choices=["lowest_latency", "round_robin", "priority", "random"], help="Load balancing policy")
    parser.add_argument("--local", action="store_true", help="Force localhost loopback addresses (127.0.0.1)")
    parser.add_argument("--timeout", type=float, default=2.0, help="Socket timeout in seconds")
    parser.add_argument("--config", help="Path to config.json")
    args = parser.parse_args()

    client = DNSResolutionClient(
        config_path=args.config,
        use_local_ip=args.local,
        policy=args.policy,
        timeout=args.timeout
    )

    if args.hostname:
        res = client.resolve(args.hostname)
        print(f"\nHostname: {res['hostname']}")
        print(f"Status: {res['status']}")
        print(f"IP: {res['ip']}")
        print(f"Source: {res['source']}")
        print(f"Total Time: {res['total_time_ms']} ms")
        sys.exit(0 if res['status'] == 'RESOLVED' else 1)
    else:
        run_interactive_client(client)


if __name__ == "__main__":
    main()

