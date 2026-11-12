"""
SDN Flow Manager Module for DNS-SDN Resolution System
Manages OpenFlow 1.3 flow tables, DNS-specific routing policies,
dynamic traffic steering, and port/flow telemetry tracking.
"""

import sys
import json
import time
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

LOG_DIR = PROJECT_ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)

logger = logging.getLogger("FlowManager")
logger.setLevel(logging.INFO)
if not logger.handlers:
    fh = logging.FileHandler(LOG_DIR / "sdn_controller.log")
    fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(logging.Formatter("[SDN-FlowManager] %(asctime)s [%(levelname)s]: %(message)s"))
    logger.addHandler(fh)
    logger.addHandler(sh)
    logger.propagate = False


class FlowManager:
    """
    Coordinates OpenFlow 1.3 flow rule specifications for DNS-SDN.
    Bridges application-level resolver health intelligence with network-level
    switch forwarding tables.
    """

    def __init__(self, config_path: Optional[str] = None):
        self.config_path = Path(config_path) if config_path else PROJECT_ROOT / "config" / "config.json"
        self.config = self._load_config()

        sdn_conf = self.config.get("sdn", {})
        self.stats_file = PROJECT_ROOT / sdn_conf.get("stats_file", "sdn/sdn_stats.json")
        self.stats_file.parent.mkdir(parents=True, exist_ok=True)
        self.idle_timeout = int(sdn_conf.get("idle_timeout_sec", 30))
        self.hard_timeout = int(sdn_conf.get("hard_timeout_sec", 60))
        self.dns_ports = sdn_conf.get("dns_udp_ports", [5000, 5001, 53])

        # Mininet port topology mapping
        # Port 1: h1 (Client)
        # Port 2: h2 (Resolver A)
        # Port 3: h3 (Resolver B)
        self.client_port = 1
        self.resolver_a_port = 2
        self.resolver_b_port = 3

        # Active primary resolver target for network-level prioritization
        self.active_resolver_name = "Resolver A"
        self.active_resolver_port = self.resolver_a_port

        # Telemetry storage
        self.port_stats: Dict[int, Dict[str, Any]] = {
            1: {"rx_packets": 0, "tx_packets": 0, "rx_bytes": 0, "tx_bytes": 0, "name": "h1-client"},
            2: {"rx_packets": 0, "tx_packets": 0, "rx_bytes": 0, "tx_bytes": 0, "name": "h2-resolver-a"},
            3: {"rx_packets": 0, "tx_packets": 0, "rx_bytes": 0, "tx_bytes": 0, "name": "h3-resolver-b"}
        }

        # Track installed flow table state
        self.installed_rules: List[Dict[str, Any]] = []
        self._init_stats_file()

    def _load_config(self) -> Dict[str, Any]:
        if self.config_path.exists():
            try:
                with open(self.config_path, "r") as f:
                    return json.load(f)
            except Exception as e:
                logger.error("Failed to load config: %s", e)
        return {}

    def _init_stats_file(self) -> None:
        """Create initial empty stats file."""
        self.record_stats_snapshot()

    def update_active_resolver(self, resolver_name: str) -> bool:
        """
        Dynamically update network-level forwarding target.
        When Resolver A fails or policy shifts, switch flow tables redirect or prioritize traffic.
        """
        resolver_name_clean = resolver_name.strip()
        if "Resolver B" in resolver_name_clean or "resolver_b" in resolver_name_clean:
            new_port = self.resolver_b_port
            norm_name = "Resolver B"
        else:
            new_port = self.resolver_a_port
            norm_name = "Resolver A"

        if norm_name != self.active_resolver_name:
            old_name = self.active_resolver_name
            self.active_resolver_name = norm_name
            self.active_resolver_port = new_port
            logger.info(
                "[SDN TRAFFIC REDIRECT] Dynamic flow update: preferred resolver changed from %s (port %d) to %s (port %d)",
                old_name, self.resolver_a_port if old_name == "Resolver A" else self.resolver_b_port,
                norm_name, new_port
            )
            self.record_stats_snapshot()
            return True
        return False

    def update_port_stats(self, port_no: int, rx_packets: int, tx_packets: int, rx_bytes: int, tx_bytes: int) -> None:
        """Record live OpenFlow port counter telemetry from the switch."""
        if port_no in self.port_stats:
            self.port_stats[port_no].update({
                "rx_packets": rx_packets,
                "tx_packets": tx_packets,
                "rx_bytes": rx_bytes,
                "tx_bytes": tx_bytes,
                "last_updated": time.time()
            })

    def record_stats_snapshot(self) -> None:
        """Atomic write of live SDN stats for visualization dashboard and benchmarks."""
        # Calculate traffic distribution
        a_packets = self.port_stats[2]["rx_packets"] + self.port_stats[2]["tx_packets"]
        b_packets = self.port_stats[3]["rx_packets"] + self.port_stats[3]["tx_packets"]
        total_resolver_packets = a_packets + b_packets

        pct_a = round((a_packets / total_resolver_packets * 100.0), 1) if total_resolver_packets > 0 else 50.0
        pct_b = round((b_packets / total_resolver_packets * 100.0), 1) if total_resolver_packets > 0 else 50.0

        snapshot = {
            "timestamp": time.time(),
            "active_resolver": self.active_resolver_name,
            "active_resolver_port": self.active_resolver_port,
            "port_statistics": self.port_stats,
            "traffic_distribution_percent": {
                "Resolver A": pct_a,
                "Resolver B": pct_b
            },
            "installed_flows_count": len(self.installed_rules),
            "congestion_detected": (a_packets > 50000 or b_packets > 50000)
        }

        temp_file = self.stats_file.with_suffix(".tmp")
        try:
            with open(temp_file, "w") as f:
                json.dump(snapshot, f, indent=4)
            temp_file.replace(self.stats_file)
        except Exception as e:
            logger.error("Failed writing SDN stats: %s", e)

    def generate_dns_flow_spec(self, client_port: int, target_resolver_port: int, udp_port: int) -> Dict[str, Any]:
        """
        Generate OpenFlow 1.3 flow specification for DNS UDP traffic.
        Priority 100 (higher than normal L2 table-miss or learning flows).
        """
        return {
            "table_id": 0,
            "priority": 100,
            "idle_timeout": self.idle_timeout,
            "hard_timeout": self.hard_timeout,
            "match": {
                "in_port": client_port,
                "eth_type": 0x0800,  # IPv4
                "ip_proto": 17,      # UDP
                "udp_dst": udp_port
            },
            "actions": [
                {"type": "OUTPUT", "port": target_resolver_port}
            ],
            "description": f"Direct DNS UDP:{udp_port} from port {client_port} to resolver port {target_resolver_port}"
        }

    def explain_architecture_difference(self) -> str:
        """
        Clarify the core networking distinction required for academic defense:
        Application-Level Resolver Selection vs. Network-Level SDN Forwarding.
        """
        return (
            "=================================================================================\n"
            "ACADEMIC ARCHITECTURAL DISTINCTION:\n"
            "1. Application-Level Selection (Client):\n"
            "   - Operates at OSI Layer 7 (Application).\n"
            "   - Client selects target socket destination (e.g. 10.0.0.20:5000 vs 10.0.0.30:5001)\n"
            "     based on cached DNS records, local policy, and health status JSON.\n\n"
            "2. Network-Level Forwarding (SDN OpenFlow Controller & Switch s1):\n"
            "   - Operates at OSI Layer 2/3/4 (Data Link, Network, Transport).\n"
            "   - Open vSwitch inspects frame headers (eth_type=0x0800, ip_proto=17, udp_dst).\n"
            "   - Ryu Controller pushes proactive/reactive OpenFlow 1.3 match-action rules.\n"
            "   - During network failover or traffic rerouting, the SDN controller can rewrite\n"
            "     packet headers, prioritize resolver queues, or redirect flows without\n"
            "     requiring changes to client software!\n"
            "================================================================================="
        )

