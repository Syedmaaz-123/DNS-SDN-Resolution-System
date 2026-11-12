"""
Health Monitor Module for DNS-SDN Resolution System
Continuously monitors resolver availability and latency via UDP PING/PONG,
implements flapping prevention with consecutive failure/recovery thresholds,
and writes health metrics atomically to JSON.
"""

import os
import sys
import time
import json
import socket
import logging
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

LOG_DIR = PROJECT_ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)

# Logger setup
logger = logging.getLogger("HealthMonitor")
logger.setLevel(logging.INFO)
if not logger.handlers:
    fh = logging.FileHandler(LOG_DIR / "health_monitor.log")
    fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s]: %(message)s"))
    logger.addHandler(fh)
    logger.addHandler(sh)
    logger.propagate = False


class HealthMonitor:
    """
    Intelligent Health Monitoring Engine for DNS Resolvers.
    Tracks availability, round-trip latency, packet loss, and state transitions.
    """

    def __init__(
        self,
        config_path: Optional[str] = None,
        use_local_ip: bool = False,
        interval: Optional[float] = None,
        timeout: Optional[float] = None,
        failure_threshold: Optional[int] = None,
        recovery_threshold: Optional[int] = None
    ):
        self.config_path = Path(config_path) if config_path else PROJECT_ROOT / "config" / "config.json"
        self.config = self._load_config()
        self.use_local_ip = use_local_ip

        # Health monitor config settings
        hm_conf = self.config.get("health_monitor", {})
        self.interval = float(interval if interval is not None else hm_conf.get("check_interval_sec", 3.0))
        self.timeout = float(timeout if timeout is not None else hm_conf.get("timeout_sec", 1.5))
        self.failure_threshold = int(failure_threshold if failure_threshold is not None else hm_conf.get("failure_threshold", 2))
        self.recovery_threshold = int(recovery_threshold if recovery_threshold is not None else hm_conf.get("recovery_threshold", 2))

        # Status file path
        status_file_rel = hm_conf.get("status_file", "monitoring/health_status.json")
        self.status_file = PROJECT_ROOT / status_file_rel
        self.status_file.parent.mkdir(parents=True, exist_ok=True)

        # Resolvers to monitor
        self.resolvers_conf = self.config.get("resolvers", {
            "Resolver A": {"ip": "10.0.0.20", "local_ip": "127.0.0.1", "port": 5000},
            "Resolver B": {"ip": "10.0.0.30", "local_ip": "127.0.0.1", "port": 5001}
        })

        # Internal persistent state
        self.state: Dict[str, Dict[str, Any]] = {}
        self._init_state()

    def _load_config(self) -> Dict[str, Any]:
        if self.config_path.exists():
            try:
                with open(self.config_path, "r") as f:
                    return json.load(f)
            except Exception as e:
                logger.error("Failed to load config: %s", e)
        return {}

    def _init_state(self) -> None:
        """Initialize state tracking for all configured resolvers."""
        for name, details in self.resolvers_conf.items():
            chosen_ip = details.get("local_ip", "127.0.0.1") if self.use_local_ip else details.get("ip", "127.0.0.1")
            self.state[name] = {
                "name": name,
                "ip": chosen_ip,
                "port": details.get("port", 5000),
                "online": True,  # Optimistic initial state
                "latency_ms": None,
                "consecutive_failures": 0,
                "consecutive_successes": 0,
                "total_probes": 0,
                "successful_probes": 0,
                "packet_loss_percent": 0.0,
                "last_seen": None,
                "last_checked": None,
                "latency_history": []  # Last 10 measurements
            }

    def check_resolver(self, name: str) -> Dict[str, Any]:
        """
        Probe a single resolver with a UDP PING packet and update its state.
        """
        srv = self.state[name]
        ip = srv["ip"]
        port = srv["port"]
        srv["total_probes"] += 1
        srv["last_checked"] = time.time()

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(self.timeout)

        is_success = False
        measured_latency = None

        try:
            start = time.perf_counter()
            sock.sendto(b"PING", (ip, port))
            response, _ = sock.recvfrom(1024)
            elapsed = (time.perf_counter() - start) * 1000

            if response.decode("utf-8").strip() == "PONG":
                is_success = True
                measured_latency = round(elapsed, 3)

        except (socket.timeout, OSError):
            is_success = False
        finally:
            sock.close()

        # Update consecutive counters and state
        previous_online = srv["online"]

        if is_success:
            srv["successful_probes"] += 1
            srv["consecutive_successes"] += 1
            srv["consecutive_failures"] = 0
            srv["latency_ms"] = measured_latency
            srv["last_seen"] = time.time()

            # Record history
            srv["latency_history"].append(measured_latency)
            if len(srv["latency_history"]) > 10:
                srv["latency_history"].pop(0)

            # Check if recovering from offline
            if not previous_online:
                if srv["consecutive_successes"] >= self.recovery_threshold:
                    srv["online"] = True
                    logger.info("[RECOVERY] %s recovered after %d successful checks!", name, srv["consecutive_successes"])
            else:
                srv["online"] = True

        else:
            srv["consecutive_failures"] += 1
            srv["consecutive_successes"] = 0
            srv["latency_ms"] = None

            # Check if failing from online
            if previous_online:
                if srv["consecutive_failures"] >= self.failure_threshold:
                    srv["online"] = False
                    logger.warning("[FAILURE] %s marked OFFLINE after %d consecutive failures.", name, srv["consecutive_failures"])
            else:
                srv["online"] = False

        # Calculate packet loss %
        lost_probes = srv["total_probes"] - srv["successful_probes"]
        srv["packet_loss_percent"] = round((lost_probes / srv["total_probes"]) * 100.0, 1)

        return srv

    def check_all(self) -> Dict[str, Any]:
        """Check all resolvers and persist status file."""
        snapshot = {
            "updated_at": time.time(),
            "updated_at_iso": datetime.now().isoformat(),
            "servers": {}
        }

        for name in list(self.state.keys()):
            srv_state = self.check_resolver(name)
            snapshot["servers"][name] = {
                "name": name,
                "ip": srv_state["ip"],
                "port": srv_state["port"],
                "online": srv_state["online"],
                "latency_ms": srv_state["latency_ms"],
                "consecutive_failures": srv_state["consecutive_failures"],
                "consecutive_successes": srv_state["consecutive_successes"],
                "total_probes": srv_state["total_probes"],
                "successful_probes": srv_state["successful_probes"],
                "packet_loss_percent": srv_state["packet_loss_percent"],
                "last_seen": srv_state["last_seen"],
                "last_checked": srv_state["last_checked"],
                "recent_latencies": srv_state["latency_history"]
            }

        self.save_status(snapshot)
        return snapshot

    def save_status(self, snapshot: Dict[str, Any]) -> None:
        """Atomic write to status file using temporary file replacement."""
        temp_file = self.status_file.with_suffix(".tmp")
        try:
            with open(temp_file, "w") as f:
                json.dump(snapshot, f, indent=4)
            os.replace(temp_file, self.status_file)
        except Exception as e:
            logger.error("Failed to write health status file: %s", e)

    def run_loop(self) -> None:
        """Continuous monitoring loop."""
        print("=" * 60)
        print("         DNS RESOLVER HEALTH MONITOR (v2.0)")
        print("=" * 60)
        print(f"  Check Interval    : {self.interval}s")
        print(f"  Probe Timeout     : {self.timeout}s")
        print(f"  Failure Threshold : {self.failure_threshold} misses")
        print(f"  Recovery Threshold: {self.recovery_threshold} hits")
        print(f"  Status File       : {self.status_file}")
        print("=" * 60)

        try:
            while True:
                snapshot = self.check_all()
                ts_str = datetime.now().strftime("%H:%M:%S")

                print(f"\n[{ts_str}] Resolver Health Snapshot:")
                for name, data in snapshot["servers"].items():
                    if data["online"]:
                        print(f"  [ONLINE]  {name:12} | IP: {data['ip']}:{data['port']} | Latency: {data['latency_ms']} ms | Loss: {data['packet_loss_percent']}%")
                    else:
                        print(f"  [OFFLINE] {name:12} | IP: {data['ip']}:{data['port']} | Failures: {data['consecutive_failures']}")

                time.sleep(self.interval)

        except KeyboardInterrupt:
            print("\nHealth monitor stopped by user.")


def main():
    parser = argparse.ArgumentParser(description="DNS Resolver Health Monitor")
    parser.add_argument("--interval", type=float, help="Check interval in seconds")
    parser.add_argument("--timeout", type=float, help="Socket timeout in seconds")
    parser.add_argument("--local", action="store_true", help="Monitor loopback IPs (127.0.0.1)")
    parser.add_argument("--once", action="store_true", help="Run a single check and exit")
    parser.add_argument("--config", help="Path to config.json")
    args = parser.parse_args()

    monitor = HealthMonitor(
        config_path=args.config,
        use_local_ip=args.local,
        interval=args.interval,
        timeout=args.timeout
    )

    if args.once:
        snapshot = monitor.check_all()
        print(json.dumps(snapshot, indent=2))
    else:
        monitor.run_loop()


if __name__ == "__main__":
    main()

