# Comprehensive Testing & Verification Guide

This guide details the validation criteria, automated test commands, and manual verification procedures for all 12 requirement scenarios defined in Section 9 of the Master Specification.

---

## 1. Automated Testing Suite

All unit and integration tests are automated using `pytest`. Execute the suite with:

```bash
pytest tests/ -v
```

Expected result:
```
tests/test_cache.py::test_positive_caching_and_hit PASSED                [  4%]
tests/test_cache.py::test_negative_caching_and_hit PASSED                [  8%]
tests/test_cache.py::test_cache_expiration PASSED                        [ 12%]
tests/test_cache.py::test_cache_invalidation PASSED                      [ 16%]
tests/test_cache.py::test_cache_capacity_and_eviction PASSED             [ 20%]
tests/test_client.py::test_client_resolution_workflow PASSED             [ 24%]
tests/test_failover.py::test_automatic_failover_and_recovery PASSED      [ 28%]
tests/test_integration.py::test_scenario_01_normal_dns_resolution PASSED [ 32%]
tests/test_integration.py::test_scenario_02_unknown_hostname PASSED      [ 36%]
tests/test_integration.py::test_scenario_03_cache_hit PASSED             [ 40%]
tests/test_integration.py::test_scenario_04_cache_expiration PASSED      [ 44%]
tests/test_integration.py::test_scenario_05_and_06_resolver_failure_and_recovery PASSED [ 48%]
tests/test_integration.py::test_scenario_07_load_balancing_policies PASSED [ 52%]
tests/test_integration.py::test_scenario_08_mininet_config_validation PASSED [ 56%]
tests/test_integration.py::test_scenario_09_sdn_flow_rule_installation PASSED [ 60%]
tests/test_integration.py::test_scenario_10_dynamic_sdn_forwarding PASSED [ 64%]
tests/test_integration.py::test_scenario_11_performance_evaluation_artifacts PASSED [ 68%]
tests/test_integration.py::test_scenario_12_full_integration PASSED      [ 72%]
tests/test_resolver.py::test_resolver_protocol_parsing PASSED            [ 76%]
tests/test_resolver.py::test_resolver_live_udp_socket PASSED             [ 80%]
tests/test_resolver.py::test_resolver_concurrent_queries PASSED          [ 84%]
tests/test_selector.py::test_lowest_latency_selection PASSED             [ 88%]
tests/test_selector.py::test_round_robin_selection PASSED                [ 92%]
tests/test_selector.py::test_offline_exclusion PASSED                    [ 96%]
tests/test_selector.py::test_stale_health_fallback PASSED                [100%]
============================== 25 passed in ~5s ==============================
```

---

## 2. Step-by-Step Manual Verification of Section 9 Requirements

### TEST 1: Normal DNS Resolution
- **Procedure:** Enter `server1.local`.
- **Command:** `python3 client/client.py --hostname server1.local --local`
- **Expected Outcome:** Client displays `Resolved IP: 192.0.2.10`, source resolver, response time in ms.
- **Pass Condition:** Status is `RESOLVED`, correct IP returned.

### TEST 2: Unknown Hostname
- **Procedure:** Enter an invalid hostname (e.g. `fakedomain.org`).
- **Command:** `python3 client/client.py --hostname fakedomain.org --local`
- **Expected Outcome:** Resolver returns `NOT_FOUND`. Client reports `Hostname does not exist`.
- **Pass Condition:** Response is `NOT_FOUND` and stored in negative cache.

### TEST 3: Positive Cache Hit
- **Procedure:** Query the same hostname twice in succession.
- **Command:**
  ```bash
  python3 client/client.py --hostname server2.local --local
  python3 client/client.py --hostname server2.local --local
  ```
- **Expected Outcome:** The second request outputs `[CACHE HIT] Valid for X seconds` and completes in `<0.05 ms` without sending UDP packets.
- **Pass Condition:** Lookup latency drops by 90%+.

### TEST 4: Cache Expiration
- **Procedure:** Wait for TTL to expire (default 100s, or test with short TTL).
- **Command:** `pytest tests/test_cache.py -k test_cache_expiration`
- **Expected Outcome:** Expired record is purged and client contacts resolver again.
- **Pass Condition:** Expired entry is never returned.

### TEST 5: Resolver A Failure
- **Procedure:** Stop Resolver A (`pkill -f "port 5000"`) while Resolver B is running.
- **Command:** Query `printer.local`.
- **Expected Outcome:** Client detects Resolver A timeout and automatically queries Resolver B.
- **Pass Condition:** Status is `RESOLVED`, `failover_occurred: True`, source is `Resolver B`.

### TEST 6: Resolver Recovery
- **Procedure:** Restart Resolver A. Wait for 2 successful health monitor checks.
- **Command:** Query `printer.local`.
- **Expected Outcome:** Resolver A is restored as preferred primary target.
- **Pass Condition:** Source is `Resolver A`, `failover_occurred: False`.

### TEST 7: Intelligent Load Balancing
- **Procedure:** Compare `--policy lowest_latency` and `--policy round_robin`.
- **Command:**
  ```bash
  python3 client/client.py --hostname database.local --policy round_robin --local
  python3 client/client.py --hostname college.local --policy round_robin --local
  ```
- **Expected Outcome:** Queries alternate between healthy resolvers. Under `lowest_latency`, the server with lowest ping is consistently selected.
- **Pass Condition:** Selection matches configured policy.

### TEST 8: Mininet Connectivity
- **Procedure:** Execute host-to-host ping in Mininet.
- **Command:** Inside `mininet_topology.py`, run `net.pingAll()`.
- **Expected Outcome:** `0% packet loss` between `h1`, `h2`, and `h3`.
- **Pass Condition:** Pingall returns 0 failures.

### TEST 9: SDN OpenFlow Forwarding
- **Procedure:** Verify OpenFlow 1.3 switch flow installation.
- **Command:** `sudo ovs-ofctl -O OpenFlow13 dump-flows s1`
- **Expected Outcome:** Table contains priority 100 flow entries matching `ip_proto=17,udp_dst=5000/5001`.
- **Pass Condition:** Matching rules present in switch flow table.

### TEST 10: Dynamic Flow Modification
- **Procedure:** Change preferred resolver in SDN controller.
- **Command:** `python3 -c "from sdn.flow_manager import FlowManager; fm = FlowManager(); fm.update_active_resolver('Resolver B')"`
- **Expected Outcome:** Controller updates active target port to port 3 and rewrites dynamic flow rules.
- **Pass Condition:** Switch port 3 receives redirected DNS traffic.

### TEST 11: Performance Benchmarks & Plots
- **Procedure:** Execute `python3 monitoring/performance_monitor.py`.
- **Expected Outcome:** 6 CSV files and 6 Matplotlib PNG charts generated in `results/`.
- **Pass Condition:** Files exist, are non-empty, and contain real measurements.

### TEST 12: Full End-to-End Integration
- **Procedure:** Run `pytest tests/test_integration.py -v`.
- **Expected Outcome:** All 12 scenarios pass in a unified test run.
- **Pass Condition:** Test session completes with zero failures.
