"""
Unit tests for Resolver Server (resolver.py).
Tests protocol parsing, PING/PONG, valid lookups, NOT_FOUND, malformed datagrams, and concurrency.
"""

import time
import socket
import threading
import pytest
from resolver.resolver import UDPResolverServer


def test_resolver_protocol_parsing():
    srv = UDPResolverServer(name="TestResolver")

    # 1. PING -> PONG
    assert srv.process_message("PING", ("127.0.0.1", 1234)) == "PONG"
    assert srv.process_message("ping", ("127.0.0.1", 1234)) == "PONG"

    # 2. RESOLVE known hostname
    assert srv.process_message("RESOLVE server1.local", ("127.0.0.1", 1234)) == "OK 192.0.2.10"
    assert srv.process_message("RESOLVE database.local", ("127.0.0.1", 1234)) == "OK 192.0.2.40"

    # 3. RESOLVE unknown hostname
    assert srv.process_message("RESOLVE nonexistent.local", ("127.0.0.1", 1234)) == "NOT_FOUND"

    # 4. Malformed commands
    assert "ERROR Empty request" in srv.process_message("", ("127.0.0.1", 1234))
    assert "ERROR Hostname missing" in srv.process_message("RESOLVE", ("127.0.0.1", 1234))
    assert "ERROR Invalid command" in srv.process_message("GET / HTTP/1.1", ("127.0.0.1", 1234))


def test_resolver_live_udp_socket(get_free_port):
    port = get_free_port()
    srv = UDPResolverServer(name="LiveResolver", host="127.0.0.1", port=port)
    t = threading.Thread(target=srv.start, daemon=True)
    t.start()
    time.sleep(0.3)

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(2.0)

    try:
        # PING check
        sock.sendto(b"PING", ("127.0.0.1", port))
        resp, _ = sock.recvfrom(1024)
        assert resp.decode("utf-8").strip() == "PONG"

        # RESOLVE check
        sock.sendto(b"RESOLVE server1.local", ("127.0.0.1", port))
        resp, _ = sock.recvfrom(1024)
        assert resp.decode("utf-8").strip() == "OK 192.0.2.10"

    finally:
        sock.close()
        srv.stop()


def test_resolver_concurrent_queries(get_free_port):
    port = get_free_port()
    srv = UDPResolverServer(name="ConcResolver", host="127.0.0.1", port=port, max_workers=5)
    t = threading.Thread(target=srv.start, daemon=True)
    t.start()
    time.sleep(0.3)

    results = []

    def client_worker(idx):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(2.0)
        try:
            s.sendto(b"RESOLVE server1.local", ("127.0.0.1", port))
            data, _ = s.recvfrom(1024)
            results.append(data.decode("utf-8").strip())
        finally:
            s.close()

    threads = [threading.Thread(target=client_worker, args=(i,)) for i in range(10)]
    for th in threads:
        th.start()
    for th in threads:
        th.join()

    srv.stop()
    assert len(results) == 10
    assert all(r == "OK 192.0.2.10" for r in results)

