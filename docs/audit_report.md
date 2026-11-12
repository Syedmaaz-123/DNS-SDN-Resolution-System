# Phase 1: Repository Audit & Gap Analysis Report

**Project Title:** DNS-SDN Resolution System: Intelligent DNS-like Resolution with Multiple Resolvers, Dynamic Load Balancing, Fault Tolerance and SDN-Controlled Network Forwarding  
**Repository Source:** https://github.com/pranav2006s/DNS-SDN-Resolution-System  
**Date:** November 2026  
**Backup Branch Created:** `backup-original`

---

## 1. Overview of Existing Codebase

The baseline repository contains 6 files:
1. `client.py` (215 lines): Simple interactive UDP DNS client with in-memory caching and basic health file reading.
2. `resolver.py` (159 lines): UDP name resolution server listening on a single port with hardcoded DNS records and ThreadPoolExecutor.
3. `health_monitor.py` (100 lines): Periodic UDP PING/PONG health prober writing status atomically to `health_status.json`.
4. `README.md` (2 lines): Minimal placeholder header.
5. `LICENSE` (MIT License).
6. `.gitignore` (Standard Python gitignore).

---

## 2. File-by-File Feature Audit Matrix

| Feature / Requirement | Baseline State in Original Repo | Status | Target State in V2 Upgrade |
|---|---|---|---|
| **UDP Client-Server Protocol** | Uses `RESOLVE <host>` -> `OK <ip>` / `NOT_FOUND` | **Implemented** | Preserve protocol format, add `STATS` command, structured logging, and non-blocking timeout handling. |
| **Two Resolvers** | Hardcoded `127.0.0.1:5000` & `5001` in client and monitor | **Partially Implemented** | Support independent hosts (`10.0.0.20` & `10.0.0.30`) in Mininet topology as well as loopback fallback. |
| **DNS Record Database** | Hardcoded Python dictionary in `resolver.py` | **Partially Implemented** | Externalize to `resolver/dns_records.json` with dynamic reload and stats. |
| **UDP PING/PONG Health Check** | Implemented in `health_monitor.py` | **Implemented** | Add consecutive failure & recovery thresholds to prevent flapping, latency smoothing, and packet loss metrics. |
| **Health Status Storage** | Stored in `health_status.json` with atomic rename | **Implemented** | Preserve atomic write pattern; enhance schema with latency history, failure count, and uptime. |
| **Client-Side Positive Caching** | Basic dictionary with monotonic expiry (`CACHE_TTL=100`) | **Implemented** | Preserve 100s TTL; move to `client/dns_cache.py`, add hit/miss counters, thread safety, and cache size limits. |
| **Negative Caching** | Non-existent (`NOT_FOUND` is not cached) | **Missing** | Implement negative caching with distinct configurable TTL (30s) in `dns_cache.py`. |
| **Cache Hit / Miss Statistics** | Printed to console only | **Missing** | Implement programmatic statistics tracking (hit count, miss count, hit ratio %, eviction count). |
| **Intelligent Load Balancing** | Simple binary `online` sort (no latency ranking, no RR) | **Partially Implemented** | Implement `client/resolver_selector.py` supporting `lowest_latency`, `round_robin`, `priority`, and `random`. |
| **Automatic Failover & Recovery** | Basic try-next-in-list on socket timeout | **Partially Implemented** | Robust failover with recovery re-entry, flapping mitigation, and failover latency measurements. |
| **Mininet Network Topology** | None (ran on localhost only) | **Missing** | Implement `mininet/mininet_topology.py` with 1 switch (`s1`), 3 hosts (`h1`, `h2`, `h3`), OpenFlow 1.3. |
| **SDN Controller Application** | None | **Missing** | Implement `sdn/sdn_controller.py` and `sdn/flow_manager.py` using OpenFlow 1.3 (Ryu/OS-Ken compatible). |
| **Resolver-Aware SDN Forwarding** | None | **Missing** | Controller inspects DNS UDP flows, prioritizes active resolver, dynamically modifies flow rules on failover. |
| **SDN Telemetry & Flow Stats** | None | **Missing** | Periodic OpenFlow port/flow statistics queries tracking packet/byte distributions across resolver ports. |
| **Performance Benchmarking** | Simple `perf_counter` printouts | **Partially Implemented** | Implement `monitoring/performance_monitor.py` with automated multi-scenario test harness and CSV exports. |
| **Matplotlib Graphical Evaluation** | None | **Missing** | Automated generator creating 6 high-resolution publication-quality PNG charts in `results/`. |
| **Web Dashboard** | None | **Missing** | Lightweight Streamlit dashboard (`dashboard/app.py`) visualizing real-time status, cache, latency, and telemetry. |
| **Centralized Configuration** | Settings scattered across Python files | **Missing** | Create `config/config.json` defining all networking, caching, and timing parameters. |
| **Automated Testing Suite** | No tests existed | **Missing** | Create comprehensive pytest suite in `tests/` covering all 12 validation requirements. |
| **Documentation & Viva Prep** | 2-line placeholder | **Missing** | Comprehensive academic `README.md`, `architecture.md`, `installation.md`, `execution_guide.md`, and 40+ Q&A `viva_questions.md`. |
| **Deployment Scripts** | None | **Missing** | Provide `install.sh`, `start_project.sh`, `stop_project.sh`, and `run_benchmarks.sh`. |

---

## 3. Preserved Working Logic

The following core algorithmic choices from the author's original project have been carefully preserved:
1. **Wire Protocol:**
   - Request: `RESOLVE <hostname>`
   - Positive response: `OK <ip>`
   - Negative response: `NOT_FOUND`
   - Health check: `PING` -> `PONG`
2. **Concurrency Model:** ThreadPoolExecutor in resolvers to handle multiple incoming client queries concurrently.
3. **Atomic File Updates:** Writing to temporary file and using `os.replace` to prevent race conditions during concurrent reads by client or controller.
4. **Cache Invalidation Semantics:** Monotonic timestamp expiration with TTL check before returning data.

