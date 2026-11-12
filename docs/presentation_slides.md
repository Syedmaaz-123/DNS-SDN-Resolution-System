# 📊 DNS-SDN Resolution System: Complete Academic Presentation Slide Deck

**File:** `DNS_SDN_Resolution_System_Presentation.pptx` (14 Widescreen 16:9 Slides)  
**Target:** Final Academic Project Defense / Viva Presentation  

---

## Slide 1: Title Slide
- **Title:** DNS-SDN Resolution System
- **Subtitle:** Intelligent DNS-like Resolution with Multiple Resolvers, Dynamic Load Balancing, Fault Tolerance and SDN-Controlled Network Forwarding
- **Technologies:** OpenFlow 1.3 | Mininet Virtualization | Ryu/OS-Ken Controller | UDP Socket Hierarchy
- **Candidate:** Syed Maaz
- **Course:** Computer Networks / Distributed Systems Curriculum

---

## Slide 2: Introduction & Project Motivation
- **Fundamental Criticality:** The Domain Name System (DNS) is foundational to IP networking, translating human-readable hostnames to IP addresses.
- **Transport Layer Protocol:** Standard DNS operates primarily over UDP (Port 53) to eliminate connection handshake latency, but inherits UDP's lack of built-in connection management.
- **Modern Availability Demands:** Mission-critical applications require continuous sub-millisecond name resolution with guaranteed zero downtime during server outages.
- **Software-Defined Networking (SDN):** Decouples control logic from underlying packet switches, enabling centralized real-time flow modification at wire speed.
- **Project Objective:** Bridge application-layer DNS intelligence with SDN OpenFlow 1.3 forwarding to deliver a fully autonomous, fault-tolerant naming system.

---

## Slide 3: Problem Statement & Baseline Limitations
- **Single Point of Failure:** Conventional DNS configurations rely on static server lists. If a primary resolver fails, clients stall on socket timeouts.
- **Lack of Negative Caching:** Queries for non-existent domains (`NOT_FOUND`) trigger repeated upstream lookups, wasting bandwidth.
- **Blind Network Forwarding:** Standard switches cannot inspect DNS payloads or reroute flows dynamically when destination servers crash.
- **Route Flapping Susceptibility:** Transient packet loss frequently causes naive monitors to rapidly toggle server states, causing routing instability.
- **Static Server Selection:** Traditional clients lack automated latency ranking and cannot shift traffic based on real-time server response times.

---

## Slide 4: Proposed Architecture & Mininet Topology
- **Control Plane:** Ryu / OS-Ken OpenFlow 1.3 Controller operating on TCP Port 6653.
- **Virtual Switching:** Single Open vSwitch (`s1`) interconnecting client and multiple resolvers.
- **Host Nodes:**
  - Host `h1` (`10.0.0.10`): DNS Resolution Client
  - Host `h2` (`10.0.0.20`): Resolver A (UDP Port 5000)
  - Host `h3` (`10.0.0.30`): Resolver B (UDP Port 5001)
- **Dual-Tier Intelligence:** Application-level client selection paired with OpenFlow network-level packet steering.

---

## Slide 5: DNS Caching & TTL Management
- **Positive Caching:** Resolved hostname-to-IP records are cached with a configurable positive TTL (Default: 100 seconds).
- **Negative Caching (RFC 2308):** Non-existent domains (`NOT_FOUND`) are cached with independent negative TTL (30 seconds), preventing query storms.
- **Thread-Safe Monotonic Design:** Protected by mutex `threading.Lock()`; expiration computed via monotonic time to prevent clock skew errors.
- **Automatic Eviction:** Enforces maximum entry limits via Least Remaining Lifetime eviction.
- **Microsecond Acceleration:** In-memory retrieval drops lookup time from ~1.2 ms down to **0.03 ms** (~50x performance increase).

---

## Slide 6: Intelligent Load Balancing & Resolver Selection
- **Lowest-Latency Policy (Default):** Dynamically sorts healthy resolvers by measured UDP PING latency, sending queries to the fastest server.
- **Round-Robin Policy:** Sequentially alternates queries across healthy nodes to distribute processing burden equally.
- **Priority Policy:** Directs traffic to primary Resolver A, falling back to Resolver B only when Resolver A is offline.
- **Health Exclusion:** Resolvers marked `OFFLINE` in health telemetry are excluded from primary candidate selection.
- **Stale Data Fallback:** If health timestamps exceed 15 seconds, the selector falls back to safe priority ordering automatically.

---

## Slide 7: Health Probing & Route Flapping Prevention
- **Active UDP Heartbeats:** Dedicated health daemon sends UDP `PING` to each resolver every 3.0 seconds and awaits `PONG`.
- **Consecutive Failure Threshold:** A server is marked `OFFLINE` only after 2 consecutive failed probes, preventing false positives from transient jitter.
- **Consecutive Recovery Threshold:** An offline server must succeed on 2 consecutive probes before being declared `ONLINE`, preventing flapping.
- **Atomic Telemetry Persistence:** Health state written to temporary file and renamed via atomic POSIX replace (`os.replace`), eliminating race conditions.
- **Telemetry Metrics:** Tracks uptime %, packet loss %, rolling latency history, and transition timestamps.

---

## Slide 8: SDN Controller & OpenFlow 1.3 Pipeline
- **Table-Miss Flow Entry (Priority 0):** Directs unclassified packets to controller via OpenFlow `Packet-In` messages.
- **Proactive DNS Flow (Priority 100):** Matches `eth_type=0x0800`, `ip_proto=17`, `udp_dst=5000/5001`. Directs client DNS queries to active resolver port.
- **Dynamic Failover Flow (Priority 200):** Pushed dynamically when health status reports server failure, rerouting packets directly at switch level.
- **Switch Telemetry Polling:** Controller polls `OFPPortStatsRequest` every 5s to record live RX/TX packets and bytes per switch port.
- **Hardware Line-Rate Forwarding:** Packet forwarding is executed directly by Open vSwitch without per-packet controller overhead once flows are installed.

---

## Slide 9: Performance Evaluation: Caching & Latency
*(Slide embeds `results/cache_hit_vs_miss.png`)*
- **Cache Miss Latency:** Network UDP round-trip latency averages **1.25 ms to 2.85 ms**.
- **Cache Hit Latency:** In-memory hash table lookup resolves in **0.02 ms to 0.04 ms**.
- **Measured Speedup:** Yields an empirical **50x to 80x acceleration factor**.
- **Network Conservation:** Reduces DNS packet traffic across the Open vSwitch by over **90%** during repeat queries.

---

## Slide 10: Performance Evaluation: Failover & Throughput
*(Slide embeds `results/failover_performance.png`)*
- **Normal Steady-State:** Queries resolve smoothly at ~1.2 ms via primary Resolver A.
- **Failover Transition:** Upon Resolver A failure, socket detects timeout and switches to Resolver B seamlessly.
- **Recovery Re-entry:** When Resolver A recovers, health monitor restores it to eligible pool without service interruption.
- **High Query Scalability:** Multithreaded query load sustains up to **19,000+ Queries Per Second (QPS)** with sub-millisecond average latency.

---

## Slide 11: Real-Time Telemetry Dashboard
*(Slide embeds `results/system_summary_dashboard.png`)*
- **Live Server Health Cards:** Displays real-time ONLINE/OFFLINE badges, current latency, and probe loss rate.
- **SDN Port Telemetry:** Monitors Open vSwitch port statistics, RX/TX bytes, and resolver traffic distribution.
- **Interactive Query Tester:** Allows examiners to type hostnames directly in the web UI and view live resolution output.
- **Empirical Visualizations:** Integrates generated Matplotlib benchmark figures directly into an interactive presentation tab.

---

## Slide 12: Verification & Automated Testing Suite
- **Comprehensive Pytest Suite:** 25 automated unit and integration tests executing across 6 test modules with **100% pass rate**.
- **Protocol Validation:** Verifies PING/PONG, valid name mappings, NOT_FOUND, and malformed command handling.
- **Caching & Eviction Tests:** Confirms positive TTL, negative TTL, capacity eviction, and thread concurrency safety.
- **Failover Scenario Tests:** Validates dynamic failover to Resolver B and seamless recovery upon Resolver A restart.
- **SDN Flow Tests:** Validates OpenFlow 1.3 Priority 100 DNS flow spec generation and priority 200 failover modification.

---

## Slide 13: Conclusion & Future Scope
- **Key Accomplishments:** Successfully integrated Application-Level DNS intelligence with OpenFlow 1.3 network-level SDN forwarding.
- **High Reliability:** Demonstrated zero-downtime failover, flapping mitigation, and ~50x caching acceleration.
- **Broad Portability:** Runs seamlessly on both native macOS/Linux and full Mininet OpenFlow topologies.
- **Future Scope 1 (DNSSEC):** Cryptographic signature verification (RRSIG/DNSKEY).
- **Future Scope 2 (Encrypted DNS):** Migration to DNS-over-HTTPS (DoH) and DNS-over-TLS (DoT).
- **Future Scope 3 (Machine Learning):** Predictive latency and congestion-aware reinforcement learning routing.

---

## Slide 14: Q&A & Thank You
- **Project Title:** DNS-SDN Resolution System
- **Repository:** https://github.com/Syedmaaz-123/DNS-SDN-Resolution-System
- **Open for Questions**
