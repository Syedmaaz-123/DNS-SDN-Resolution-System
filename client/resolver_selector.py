"""
Resolver Selection & Intelligent Load Balancing Module
Implements health-aware server ranking, lowest-latency selection,
round-robin balancing, priority ordering, and automatic failover tracking.
"""

import json
import time
import random
import threading
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Any


class ResolverSelector:
    """
    Intelligent Resolver Selector for DNS-SDN Resolution System.
    Evaluates resolver health, historical latency, and active policies
    to determine the optimal resolution target.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None, config_path: Optional[str] = None):
        self.config_path = config_path or str(Path(__file__).resolve().parent.parent / "config" / "config.json")
        self.config = config or self._load_config()

        # Extract resolvers
        self.resolvers = self.config.get("resolvers", {
            "Resolver A": {"id": "resolver_a", "ip": "10.0.0.20", "local_ip": "127.0.0.1", "port": 5000, "priority": 1},
            "Resolver B": {"id": "resolver_b", "ip": "10.0.0.30", "local_ip": "127.0.0.1", "port": 5001, "priority": 2}
        })

        # Load balancing settings
        lb_conf = self.config.get("load_balancing", {})
        self.default_policy = lb_conf.get("default_policy", "lowest_latency")
        self.stale_threshold = float(lb_conf.get("stale_health_threshold_sec", 15.0))

        # Health status file path
        hm_conf = self.config.get("health_monitor", {})
        status_file_rel = hm_conf.get("status_file", "monitoring/health_status.json")
        self.status_file = Path(__file__).resolve().parent.parent / status_file_rel

        # State tracking
        self._round_robin_index = 0
        self._rr_lock = threading.Lock()
        self.last_selected_resolver: Optional[str] = None
        self.selection_history: List[Dict[str, Any]] = []

    def _load_config(self) -> Dict[str, Any]:
        """Safely load JSON configuration."""
        try:
            with open(self.config_path, "r") as f:
                return json.load(f)
        except Exception:
            return {}

    def get_health_data(self) -> Tuple[Dict[str, Any], bool, str]:
        """
        Read health status from health_status.json.
        Returns:
            Tuple: (health_dict, is_fresh, message)
        """
        if not self.status_file.exists():
            return {}, False, f"Health file '{self.status_file}' does not exist"

        try:
            with open(self.status_file, "r") as f:
                status = json.load(f)

            updated_at = status.get("updated_at", 0)
            age = time.time() - updated_at

            if age > self.stale_threshold:
                return status.get("servers", {}), False, f"Health status is stale ({age:.1f}s > {self.stale_threshold}s threshold)"

            return status.get("servers", {}), True, f"Health status is fresh (updated {age:.1f}s ago)"

        except Exception as e:
            return {}, False, f"Failed to parse health status file: {e}"

    def get_candidate_servers(self, use_local_ip: bool = False) -> List[Dict[str, Any]]:
        """Return standardized list of resolver dictionaries."""
        candidates = []
        for name, info in self.resolvers.items():
            chosen_ip = info.get("local_ip", "127.0.0.1") if use_local_ip else info.get("ip", "127.0.0.1")
            candidates.append({
                "name": name,
                "id": info.get("id", name.lower().replace(" ", "_")),
                "ip": chosen_ip,
                "port": info.get("port", 5000),
                "priority": info.get("priority", 999)
            })
        return candidates

    def select_resolver(
        self,
        policy: Optional[str] = None,
        use_local_ip: bool = False
    ) -> Tuple[Dict[str, Any], List[Dict[str, Any]], str]:
        """
        Select the best resolver according to the chosen policy and return full failover sequence.

        Args:
            policy: 'lowest_latency', 'round_robin', 'priority', or 'random' (defaults to config)
            use_local_ip: if True, use loopback IPs (for localhost testing without Mininet)

        Returns:
            Tuple: (primary_server, complete_fallback_order, explanation_string)
        """
        effective_policy = policy or self.default_policy
        candidates = self.get_candidate_servers(use_local_ip=use_local_ip)
        health_data, is_fresh, health_msg = self.get_health_data()

        # Separate candidates into healthy and unhealthy
        healthy_candidates = []
        unhealthy_candidates = []

        for server in candidates:
            s_name = server["name"]
            server_health = health_data.get(s_name, {})

            # If health data is fresh, use reported status; otherwise assume healthy if unreachable
            is_online = server_health.get("online", True) if is_fresh else True
            latency_ms = server_health.get("latency_ms") if is_fresh else None

            enriched_server = dict(server)
            enriched_server["online"] = is_online
            enriched_server["latency_ms"] = latency_ms

            if is_online:
                healthy_candidates.append(enriched_server)
            else:
                unhealthy_candidates.append(enriched_server)

        explanation = ""

        # Handle case where all servers are marked offline
        if not healthy_candidates:
            explanation = f"CRITICAL: All resolvers reported offline in {self.status_file.name}. Falling back to default order."
            ordered_servers = sorted(candidates, key=lambda s: s["priority"])
            primary = ordered_servers[0]
            return primary, ordered_servers, explanation

        # Apply selection policy to healthy servers
        if effective_policy == "lowest_latency":
            # Sort healthy servers by latency ascending; None latencies placed at the end
            def sort_key(s):
                lat = s.get("latency_ms")
                return (lat is None, lat if lat is not None else 9999.0, s["priority"])

            healthy_candidates.sort(key=sort_key)
            primary = healthy_candidates[0]
            lat_str = f"{primary['latency_ms']:.2f} ms" if primary.get("latency_ms") is not None else "unknown ms"
            explanation = (
                f"Selected {primary['name']} ({primary['ip']}:{primary['port']}) "
                f"based on lowest measured latency ({lat_str}) under policy '{effective_policy}'."
            )

        elif effective_policy == "round_robin":
            with self._rr_lock:
                idx = self._round_robin_index % len(healthy_candidates)
                self._round_robin_index += 1
            # Reorder list starting from chosen index
            healthy_candidates = healthy_candidates[idx:] + healthy_candidates[:idx]
            primary = healthy_candidates[0]
            explanation = (
                f"Selected {primary['name']} ({primary['ip']}:{primary['port']}) "
                f"via round-robin sequence (index {idx + 1}/{len(healthy_candidates)})."
            )

        elif effective_policy == "priority":
            healthy_candidates.sort(key=lambda s: s["priority"])
            primary = healthy_candidates[0]
            explanation = (
                f"Selected {primary['name']} ({primary['ip']}:{primary['port']}) "
                f"based on highest configured priority (rank {primary['priority']})."
            )

        elif effective_policy == "random":
            primary = random.choice(healthy_candidates)
            # Put primary at front
            healthy_candidates.remove(primary)
            healthy_candidates.insert(0, primary)
            explanation = f"Selected {primary['name']} ({primary['ip']}:{primary['port']}) randomly."

        else:
            primary = healthy_candidates[0]
            explanation = f"Selected {primary['name']} using fallback selection."

        # The complete failover list: healthy in chosen order, followed by any unhealthy
        complete_order = healthy_candidates + unhealthy_candidates

        # Record selection
        self.last_selected_resolver = primary["name"]
        self.selection_history.append({
            "timestamp": time.time(),
            "selected": primary["name"],
            "policy": effective_policy,
            "latency": primary.get("latency_ms"),
            "health_info": health_msg
        })

        return primary, complete_order, explanation
