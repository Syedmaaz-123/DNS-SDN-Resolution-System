"""
Mininet Network Topology for DNS-SDN Resolution System
Defines a 1-switch, 3-host OpenFlow 1.3 topology connecting the DNS client (h1),
Resolver A (h2), and Resolver B (h3) to an OpenFlow switch (s1) managed by a remote SDN controller.
"""

import sys
import time
import os
import argparse
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Detect Mininet availability (native on Linux)
HAS_MININET = False
try:
    from mininet.topo import Topo
    from mininet.net import Mininet
    from mininet.node import RemoteController, OVSSwitch
    from mininet.cli import CLI
    from mininet.log import setLogLevel, info
    from mininet.clean import cleanup
    HAS_MININET = True
except ImportError:
    HAS_MININET = False


if HAS_MININET:
    class DNSSDNTypology(Topo):
        """
        OpenFlow 1.3 Topology:
            h1 (10.0.0.10) <--- port 1 ---> [ s1 ] <--- port 2 ---> h2 (10.0.0.20 - Resolver A)
                                              |
                                              +-------- port 3 ---> h3 (10.0.0.30 - Resolver B)
        """

        def build(self):
            # Add OpenFlow switch s1 with OpenFlow 1.3
            s1 = self.addSwitch("s1", protocols="OpenFlow13")

            # Add hosts with static IPs and MAC addresses
            h1 = self.addHost("h1", ip="10.0.0.10/24", mac="00:00:00:00:00:01")
            h2 = self.addHost("h2", ip="10.0.0.20/24", mac="00:00:00:00:00:02")
            h3 = self.addHost("h3", ip="10.0.0.30/24", mac="00:00:00:00:00:03")

            # Connect hosts to specific switch ports
            self.addLink(h1, s1, port1=0, port2=1)
            self.addLink(h2, s1, port1=0, port2=2)
            self.addLink(h3, s1, port1=0, port2=3)


def start_network(cli_mode: bool = True, auto_start: bool = False, controller_ip: str = "127.0.0.1", controller_port: int = 6653):
    """Launch Mininet topology with Open vSwitch and Remote Controller."""
    if not HAS_MININET:
        print("\n" + "=" * 65)
        print("MININET ENVIRONMENT NOTICE:")
        print("Mininet and Open vSwitch require a Linux environment (e.g., Ubuntu 20.04/22.04/24.04).")
        print("On macOS or non-Linux host, please run inside an Ubuntu VM or container.")
        print("See docs/installation.md and docs/execution_guide.md for detailed setup instructions.")
        print("=" * 65 + "\n")
        return False

    setLogLevel("info")
    cleanup()

    info("*** Initializing DNS-SDN OpenFlow 1.3 Topology...\n")
    topo = DNSSDNTypology()

    controller = RemoteController(
        name="c0",
        ip=controller_ip,
        port=controller_port
    )

    net = Mininet(
        topo=topo,
        switch=OVSSwitch,
        controller=controller,
        autoSetMacs=True,
        autoStaticArp=True
    )

    info("*** Starting Network & OpenFlow Switch (s1)...\n")
    net.start()

    # Configure OpenFlow 1.3 on switch s1 explicitly
    s1 = net.get("s1")
    s1.cmd("ovs-vsctl set bridge s1 protocols=OpenFlow13")

    h1 = net.get("h1")
    h2 = net.get("h2")
    h3 = net.get("h3")

    info("\n" + "=" * 60 + "\n")
    info("  DNS-SDN MININET NETWORK READY\n")
    info(f"  h1 (Client)     : IP={h1.IP()} MAC={h1.MAC()} Connected to s1 port 1\n")
    info(f"  h2 (Resolver A) : IP={h2.IP()} MAC={h2.MAC()} Connected to s1 port 2\n")
    info(f"  h3 (Resolver B) : IP={h3.IP()} MAC={h3.MAC()} Connected to s1 port 3\n")
    info(f"  Controller      : {controller_ip}:{controller_port} (OpenFlow 1.3)\n")
    info("=" * 60 + "\n")

    if auto_start:
        info("*** Auto-starting Resolver A on h2 (port 5000)...\n")
        h2.cmd(f"python3 {PROJECT_ROOT}/resolver/resolver.py --name 'Resolver A' --host 10.0.0.20 --port 5000 > {PROJECT_ROOT}/logs/resolver_a_mn.log 2>&1 &")

        info("*** Auto-starting Resolver B on h3 (port 5001)...\n")
        h3.cmd(f"python3 {PROJECT_ROOT}/resolver/resolver.py --name 'Resolver B' --host 10.0.0.30 --port 5001 > {PROJECT_ROOT}/logs/resolver_b_mn.log 2>&1 &")

        info("*** Auto-starting Health Monitor in background...\n")
        h1.cmd(f"python3 {PROJECT_ROOT}/monitoring/health_monitor.py > {PROJECT_ROOT}/logs/health_monitor_mn.log 2>&1 &")

        time.sleep(2)
        info("*** Resolvers and Health Monitor are running inside their respective hosts!\n")
        info("    You can test resolution on h1 by typing:\n")
        info("    h1 python3 client/client.py --hostname server1.local\n\n")

    if cli_mode:
        CLI(net)

    info("*** Stopping network...\n")
    net.stop()
    cleanup()
    return True


def run_automated_mininet_test():
    """Automated integration test executed inside Mininet."""
    if not HAS_MININET:
        print("[SKIP] Mininet is not installed in the current environment.")
        return False

    setLogLevel("warning")
    cleanup()

    topo = DNSSDNTypology()
    controller = RemoteController("c0", ip="127.0.0.1", port=6653)
    net = Mininet(topo=topo, switch=OVSSwitch, controller=controller, autoSetMacs=True, autoStaticArp=True)
    net.start()

    s1 = net.get("s1")
    s1.cmd("ovs-vsctl set bridge s1 protocols=OpenFlow13")

    h1, h2, h3 = net.get("h1", "h2", "h3")

    print("[TEST] Testing host-to-host IP ping connectivity...")
    ping_res = net.pingAll()
    assert ping_res == 0, f"Pingall failed: {ping_res}% packet loss"
    print("  -> Connectivity verified: 0% packet loss.")

    print("[TEST] Starting Resolver A on h2 (10.0.0.20:5000)...")
    h2.cmd(f"python3 {PROJECT_ROOT}/resolver/resolver.py --name 'Resolver A' --host 10.0.0.20 --port 5000 &")

    print("[TEST] Starting Resolver B on h3 (10.0.0.30:5001)...")
    h3.cmd(f"python3 {PROJECT_ROOT}/resolver/resolver.py --name 'Resolver B' --host 10.0.0.30 --port 5001 &")
    time.sleep(1.5)

    print("[TEST] Querying Resolver A from h1 for 'server1.local'...")
    out1 = h1.cmd(f"python3 {PROJECT_ROOT}/client/client.py --hostname server1.local")
    print("  Client Output:", out1.strip())
    assert "192.0.2.10" in out1, "Resolution failed"

    print("[TEST] Testing cache hit on h1...")
    out2 = h1.cmd(f"python3 {PROJECT_ROOT}/client/client.py --hostname server1.local")
    print("  Second query:", out2.strip())
    assert "192.0.2.10" in out2, "Second query failed"

    print("[TEST] Killing Resolver A on h2 to test failover...")
    h2.cmd("pkill -f resolver.py")
    time.sleep(1)

    print("[TEST] Querying from h1 (expecting failover to Resolver B)...")
    out3 = h1.cmd(f"python3 {PROJECT_ROOT}/client/client.py --hostname server2.local")
    print("  Failover query:", out3.strip())
    assert "192.0.2.20" in out3 or "Resolved" in out3

    net.stop()
    cleanup()
    print("[SUCCESS] All Mininet automated integration tests passed!")
    return True


def main():
    parser = argparse.ArgumentParser(description="DNS-SDN Mininet Topology Runner")
    parser.add_argument("--cli", action="store_true", default=True, help="Drop into interactive Mininet CLI")
    parser.add_argument("--auto-start", action="store_true", help="Automatically start resolvers and monitor")
    parser.add_argument("--test", action="store_true", help="Run automated integration tests and exit")
    parser.add_argument("--controller-ip", default="127.0.0.1", help="SDN Controller IP")
    parser.add_argument("--controller-port", type=int, default=6653, help="SDN Controller Port")
    args = parser.parse_args()

    if args.test:
        run_automated_mininet_test()
    else:
        start_network(
            cli_mode=args.cli,
            auto_start=args.auto_start,
            controller_ip=args.controller_ip,
            controller_port=args.controller_port
        )


if __name__ == "__main__":
    main()
