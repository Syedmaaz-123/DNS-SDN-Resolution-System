"""
Unit and Integration tests for SDN Controller & Flow Manager (test_sdn.py).
Verifies OpenFlow 1.3 flow-rule installation, dynamic traffic redirection,
port telemetry tracking, and controller-switch protocol handshake.
"""

import json
import time
import socket
import struct
import threading
import pytest
from pathlib import Path

from sdn.flow_manager import FlowManager
from sdn.sdn_controller import StandaloneOpenFlow13Controller


def test_sdn_flow_manager_dns_spec():
    """Verify priority 100 proactive DNS flow rule specification."""
    fm = FlowManager()
    spec = fm.generate_dns_flow_spec(client_port=1, target_resolver_port=2, udp_port=5000)

    assert spec["priority"] == 100
    assert spec["table_id"] == 0
    assert spec["match"]["in_port"] == 1
    assert spec["match"]["eth_type"] == 0x0800  # IPv4
    assert spec["match"]["ip_proto"] == 17      # UDP
    assert spec["match"]["udp_dst"] == 5000
    assert spec["actions"][0]["type"] == "OUTPUT"
    assert spec["actions"][0]["port"] == 2


def test_sdn_dynamic_forwarding_update():
    """Verify dynamic flow modification when preferred resolver switches."""
    fm = FlowManager()
    assert fm.active_resolver_name == "Resolver A"
    assert fm.active_resolver_port == 2

    # Switch to Resolver B
    changed = fm.update_active_resolver("Resolver B")
    assert changed is True
    assert fm.active_resolver_name == "Resolver B"
    assert fm.active_resolver_port == 3

    # Generate redirected flow rule targeting port 3
    rule_b = fm.generate_dns_flow_spec(client_port=1, target_resolver_port=fm.active_resolver_port, udp_port=5000)
    assert rule_b["actions"][0]["port"] == 3

    # Switching to same resolver returns False (no flapping / redundant writes)
    assert fm.update_active_resolver("Resolver B") is False


def test_sdn_port_statistics_telemetry():
    """Verify OpenFlow port counters and traffic distribution computation."""
    fm = FlowManager()
    fm.update_port_stats(port_no=1, rx_packets=100, tx_packets=100, rx_bytes=6400, tx_bytes=6400)
    fm.update_port_stats(port_no=2, rx_packets=80, tx_packets=80, rx_bytes=5120, tx_bytes=5120)
    fm.update_port_stats(port_no=3, rx_packets=20, tx_packets=20, rx_bytes=1280, tx_bytes=1280)

    fm.record_stats_snapshot()
    assert fm.stats_file.exists()

    with open(fm.stats_file, "r") as f:
        data = json.load(f)

    assert data["port_statistics"]["1"]["rx_packets"] == 100
    assert data["port_statistics"]["2"]["rx_packets"] == 80
    assert data["port_statistics"]["3"]["rx_packets"] == 20
    assert data["traffic_distribution_percent"]["Resolver A"] == 80.0
    assert data["traffic_distribution_percent"]["Resolver B"] == 20.0


def test_standalone_controller_openflow13_handshake(get_free_port):
    """Verify OpenFlow 1.3 switch connection and Hello message exchange."""
    port = get_free_port()
    ctrl = StandaloneOpenFlow13Controller(host="127.0.0.1", port=port)
    t = threading.Thread(target=ctrl.start, daemon=True)
    t.start()
    time.sleep(0.3)

    # Emulate an OpenFlow 1.3 switch connecting to controller
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(2.0)
    try:
        s.connect(("127.0.0.1", port))

        # Receive OFPT_HELLO from controller (Version 0x04 = OF1.3, Type 0 = HELLO)
        header = s.recv(8)
        assert len(header) == 8
        version, msg_type, msg_len, xid = struct.unpack("!BBHI", header)
        assert version == 0x04  # OpenFlow 1.3
        assert msg_type == 0    # OFPT_HELLO

        # Receive OFPT_FEATURES_REQUEST (Type 5)
        feat_req = s.recv(8)
        v_feat, t_feat, l_feat, xid_feat = struct.unpack("!BBHI", feat_req)
        assert v_feat == 0x04
        assert t_feat == 5      # OFPT_FEATURES_REQUEST

    finally:
        s.close()
        ctrl.stop()
