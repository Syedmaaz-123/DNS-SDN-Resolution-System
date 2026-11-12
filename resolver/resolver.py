"""
UDP Name Resolution Server Module for DNS-SDN Resolution System
Supports independent execution of Resolver A and Resolver B, configurable IPs/ports,
JSON-based records database, PING/PONG health checks, concurrent request processing,
and detailed query logging.
"""

import sys
import json
import signal
import socket
import logging
import argparse
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Optional, Tuple, Any

# Ensure project root in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

LOG_DIR = PROJECT_ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)


class UDPResolverServer:
    """
    Multithreaded UDP DNS-like Resolver Server.
    Processes name lookups, health-check PINGs, and diagnostic commands.
    """

    def __init__(
        self,
        name: str = "Resolver A",
        host: str = "0.0.0.0",
        port: int = 5000,
        records_path: Optional[str] = None,
        max_workers: int = 10,
        buffer_size: int = 1024
    ):
        self.name = name
        self.host = host
        self.port = port
        self.buffer_size = buffer_size
        self.max_workers = max_workers
        self.records_path = Path(records_path) if records_path else PROJECT_ROOT / "resolver" / "dns_records.json"

        # Server metrics
        self.stats = {
            "total_requests": 0,
            "resolve_queries": 0,
            "resolved_success": 0,
            "not_found": 0,
            "ping_requests": 0,
            "malformed_requests": 0,
            "started_at": time_now_str()
        }

        # Setup server logger
        safe_name = name.lower().replace(" ", "_")
        self.logger = logging.getLogger(f"Resolver-{safe_name}")
        self.logger.setLevel(logging.INFO)
        # Avoid duplicate handlers if instantiated multiple times in tests
        if not self.logger.handlers:
            log_file = LOG_DIR / f"{safe_name}.log"
            fh = logging.FileHandler(log_file)
            fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
            sh = logging.StreamHandler(sys.stdout)
            sh.setFormatter(logging.Formatter(f"[{name}] %(asctime)s [%(levelname)s]: %(message)s"))
            self.logger.addHandler(fh)
            self.logger.addHandler(sh)
            self.logger.propagate = False

        # Load database
        self.dns_records: Dict[str, str] = self.load_records()
        self._running = False
        self._socket: Optional[socket.socket] = None

    def load_records(self) -> Dict[str, str]:
        """Load hostname-to-IP mappings from JSON file."""
        if self.records_path.exists():
            try:
                with open(self.records_path, "r") as f:
                    data = json.load(f)
                    # Normalize keys to lowercase
                    records = {k.lower().strip(): v.strip() for k, v in data.items()}
                    self.logger.info("Loaded %d DNS records from '%s'", len(records), self.records_path.name)
                    return records
            except Exception as e:
                self.logger.error("Failed to parse '%s': %s. Using default baseline records.", self.records_path, e)

        # Baseline fallback records
        fallback = {
            "server1.local": "192.0.2.10",
            "server2.local": "192.0.2.20",
            "printer.local": "192.0.2.30",
            "database.local": "192.0.2.40",
            "college.local": "192.0.2.50"
        }
        self.logger.warning("Using built-in default records (5 mappings).")
        return fallback

    def reload_records(self) -> int:
        """Reload records from disk dynamically."""
        self.dns_records = self.load_records()
        return len(self.dns_records)

    def process_message(self, message: str, client_addr: Tuple[str, int]) -> str:
        """
        Parse and generate response for a decoded message string.

        Supported Protocol Commands:
            - PING                     -> PONG
            - RESOLVE <hostname>       -> OK <ip>  OR  NOT_FOUND
            - STATS                    -> JSON string of server metrics
            - RELOAD                   -> OK RELOADED <count>
        """
        self.stats["total_requests"] += 1
        parts = message.strip().split(maxsplit=1)

        if not parts:
            self.stats["malformed_requests"] += 1
            return "ERROR Empty request"

        command = parts[0].upper()

        if command == "PING":
            self.stats["ping_requests"] += 1
            return "PONG"

        elif command == "RESOLVE":
            self.stats["resolve_queries"] += 1
            if len(parts) != 2 or not parts[1].strip():
                self.stats["malformed_requests"] += 1
                return "ERROR Hostname missing"

            hostname = parts[1].strip().lower()

            if hostname in self.dns_records:
                ip = self.dns_records[hostname]
                self.stats["resolved_success"] += 1
                self.logger.info("RESOLVE '%s' -> '%s' for client %s", hostname, ip, client_addr)
                return f"OK {ip}"
            else:
                self.stats["not_found"] += 1
                self.logger.info("RESOLVE '%s' -> NOT_FOUND for client %s", hostname, client_addr)
                return "NOT_FOUND"

        elif command == "STATS":
            return f"STATS {json.dumps(self.stats)}"

        elif command == "RELOAD":
            count = self.reload_records()
            return f"OK RELOADED {count}"

        else:
            self.stats["malformed_requests"] += 1
            self.logger.warning("Unknown command '%s' from %s", command, client_addr)
            return "ERROR Invalid command"

    def handle_client_datagram(self, data: bytes, client_addr: Tuple[str, int]) -> None:
        """Process datagram and send reply over the server socket."""
        try:
            message = data.decode("utf-8")
        except UnicodeDecodeError:
            self.stats["malformed_requests"] += 1
            self.logger.warning("Received invalid encoding from %s", client_addr)
            if self._socket:
                try:
                    self._socket.sendto(b"ERROR Invalid encoding", client_addr)
                except OSError:
                    pass
            return

        response = self.process_message(message, client_addr)

        if self._socket:
            try:
                self._socket.sendto(response.encode("utf-8"), client_addr)
            except OSError as err:
                self.logger.error("Failed sending response to %s: %s", client_addr, err)

    def start(self) -> None:
        """Start listening for incoming UDP datagrams."""
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Allow address reuse
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        try:
            self._socket.bind((self.host, self.port))
        except OSError as e:
            self.logger.critical("Cannot bind to %s:%d: %s", self.host, self.port, e)
            print(f"\n[FATAL] Port {self.port} on {self.host} is already in use or unavailable: {e}")
            raise

        self._running = True

        print("=" * 55)
        print(f"       UDP NAME RESOLUTION SERVER - {self.name.upper()}")
        print("=" * 55)
        print(f"  Bound address   : {self.host}:{self.port}")
        print(f"  Records loaded  : {len(self.dns_records)}")
        print(f"  Worker threads  : {self.max_workers}")
        print(f"  Log file        : {LOG_DIR / (self.name.lower().replace(' ', '_') + '.log')}")
        print("  Ready for client requests and health checks...")
        print("=" * 55)

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            try:
                while self._running:
                    try:
                        data, client_addr = self._socket.recvfrom(self.buffer_size)
                        executor.submit(self.handle_client_datagram, data, client_addr)
                    except OSError:
                        if not self._running:
                            break
                        raise
            except KeyboardInterrupt:
                print(f"\n[{self.name}] Interrupted. Shutting down...")
            finally:
                self.stop()

    def stop(self) -> None:
        """Stop server and release socket."""
        self._running = False
        if self._socket:
            try:
                self._socket.close()
            except Exception:
                pass
            self._socket = None
        self.logger.info("Server stopped.")
        print(f"[{self.name}] Server stopped.")


def time_now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def main():
    parser = argparse.ArgumentParser(description="UDP Name Resolution Server")
    parser.add_argument("--name", default="Resolver A", help="Server display name")
    parser.add_argument("--host", default="0.0.0.0", help="IP address to bind")
    parser.add_argument("--port", type=int, default=5000, help="UDP port")
    parser.add_argument("--records", help="Path to JSON DNS records file")
    parser.add_argument("--workers", type=int, default=10, help="Worker thread pool size")
    args = parser.parse_args()

    server = UDPResolverServer(
        name=args.name,
        host=args.host,
        port=args.port,
        records_path=args.records,
        max_workers=args.workers
    )

    # Register signal handlers for graceful exit
    def sig_handler(sig, frame):
        print(f"\nReceived signal {sig}. Exiting...")
        server.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, sig_handler)
    signal.signal(signal.SIGTERM, sig_handler)

    try:
        server.start()
    except OSError:
        sys.exit(1)


if __name__ == "__main__":
    main()
