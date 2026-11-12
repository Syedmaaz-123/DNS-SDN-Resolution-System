# Comprehensive Academic Viva Questions & Answers (45 Q&As)

**Subject:** Computer Networks, Software-Defined Networking (SDN), Distributed Systems  
**Project:** DNS-SDN Resolution System  
**Coverage:** DNS, UDP, Caching & TTL, Load Balancing, Fault Tolerance, Mininet, OpenFlow 1.3, Ryu/OS-Ken Controller, Network Performance Benchmarking  

---

## Category 1: DNS & Transport Layer Protocols (Questions 1–8)

### Q1: What is the primary purpose of DNS in computer networks?
**Answer:** The Domain Name System (DNS) is a hierarchical, decentralized naming system that translates human-readable hostnames (e.g., `server1.local`) into machine-readable IP addresses (e.g., `192.0.2.10`), enabling network applications to locate and establish communication with endpoints.

### Q2: Why does DNS primarily use UDP rather than TCP for standard queries?
**Answer:** UDP is a connectionless, lightweight transport protocol with zero connection establishment overhead (no 3-way handshake). Because typical DNS queries consist of a single request and a single response datagram, UDP minimizes latency and server memory consumption. TCP is reserved for zone transfers (AXFR), DNSSEC, or responses exceeding the maximum UDP packet payload (512 bytes in classical DNS or EDNS0 buffer limits).

### Q3: What is the wire protocol format implemented in this project?
**Answer:** The system implements an application-layer UDP protocol:
- Request: `RESOLVE <hostname>`
- Positive response: `OK <ip_address>`
- Negative response: `NOT_FOUND`
- Health probe: `PING` -> `PONG`
- Administrative: `STATS` -> JSON counters, `RELOAD` -> dynamic record refresh.

### Q4: How does this project handle malformed or invalid client requests?
**Answer:** The resolver parses requests with strict token validation:
- Empty packets return `ERROR Empty request`.
- Missing parameters return `ERROR Hostname missing`.
- Unrecognized verbs return `ERROR Invalid command`.
- Corrupted byte streams return `ERROR Invalid encoding`.

### Q5: How does concurrent request processing work inside the resolver?
**Answer:** The resolver utilizes a Python `ThreadPoolExecutor` with a pool of pre-allocated worker threads. When the UDP socket receives a datagram via `recvfrom()`, the task is immediately submitted to the thread pool, allowing concurrent resolution without blocking the main socket listener thread.

### Q6: What is the difference between an authoritative name server and a recursive resolver?
**Answer:** An authoritative server holds the actual DNS zone records (the source of truth) for a specific domain. A recursive resolver acts as an intermediary on behalf of a client, querying authoritative servers in hierarchy (Root, TLD, Authoritative) and caching the results. In our project, Resolver A and Resolver B act as authoritative resolvers for the `.local` pseudo-domain.

### Q7: What are the vulnerabilities of standard UDP-based DNS?
**Answer:** UDP lacks built-in authentication and encryption, exposing queries to IP spoofing, DNS cache poisoning (Kaminsky attacks), eavesdropping, and UDP amplification Distributed Denial of Service (DDoS) attacks.

### Q8: What is EDNS0?
**Answer:** Extension Mechanisms for DNS (EDNS0, RFC 6891) extends DNS flags, label types, and return codes while expanding the maximum UDP packet size beyond the legacy 512-byte limit (often up to 1232 or 4096 bytes) without requiring fallback to TCP.

---

## Category 2: DNS Caching, Expiration, & Negative Caching (Questions 9–14)

### Q9: What is client-side DNS caching, and why is it critical?
**Answer:** Client-side caching stores previously resolved hostname-to-IP records in client memory for the duration of their Time-To-Live (TTL). It eliminates repetitive network round-trips, slashes application lookup latency from milliseconds to microseconds, and reduces upstream traffic load on resolver servers.

### Q10: How does Time-To-Live (TTL) expiration work in your implementation?
**Answer:** When an entry is cached, its expiration timestamp is computed as `created_at + ttl_seconds` using `time.monotonic()` to prevent clock skew issues. Upon retrieval, the cache calculates remaining TTL: if `monotonic() >= expires_at`, the entry is purged, an expiration counter is incremented, and a cache miss is returned. Expired data is strictly never returned.

### Q11: What is Negative Caching, and why was it added to this upgrade?
**Answer:** Defined in RFC 2308, negative caching stores the *absence* of a record (`NOT_FOUND`). Without negative caching, a misconfigured client querying an invalid hostname would repeatedly hammer the resolver network. By caching negative results with a dedicated TTL (default 30 seconds), repeat queries for non-existent domains are resolved locally.

### Q12: Why should negative cache TTL typically be shorter than positive cache TTL?
**Answer:** Positive records are generally stable configurations, warranting longer TTLs (e.g., 100 seconds). Negative states often occur temporarily due to replication delays, newly registered hosts, or temporary outages. A shorter negative TTL (e.g., 30s) prevents extended lock-out if the record is created shortly after a failed lookup.

### Q13: What happens when the cache reaches its maximum capacity?
**Answer:** The cache enforces capacity limits via a two-stage eviction policy: it first purges any expired entries. If still at capacity (`len >= max_entries`), it evicts the entry with the nearest expiration deadline (Least Remaining Lifetime), recording an eviction metric.

### Q14: How is thread safety ensured in the DNS cache module?
**Answer:** The `DNSCache` class encapsulates all dictionary modifications and statistical counter increments inside a `threading.Lock()` mutex context manager, guaranteeing atomic operations across concurrent client threads.

---

## Category 3: Health Monitoring, Flapping, & Failover (Questions 15–21)

### Q15: How does the Health Monitor probe resolver status?
**Answer:** The health monitor runs as a background daemon, periodically (default every 3 seconds) dispatching UDP `PING` datagrams to each resolver's socket and awaiting a matching `PONG` response before a configurable timeout (default 1.5 seconds). Round-trip latency is recorded via high-resolution monotonic clocks (`time.perf_counter()`).

### Q16: What is route/health flapping, and how does your project prevent it?
**Answer:** Flapping occurs when transient network jitter causes a server to rapidly alternate between ONLINE and OFFLINE states, causing unstable switching. Our project mitigates flapping using consecutive failure and recovery hysteresis thresholds:
- **Failure Threshold (2 misses):** A resolver is only marked OFFLINE after 2 consecutive timeouts.
- **Recovery Threshold (2 hits):** An offline resolver is only restored to ONLINE after 2 consecutive successful probes.

### Q17: How is concurrency and file corruption avoided when saving health status?
**Answer:** The monitor writes JSON status to a temporary file (`health_status.json.tmp`) and executes an atomic POSIX filesystem rename (`os.replace`) to `health_status.json`. This ensures that reading processes (Client, Controller, Dashboard) never read a partially written or corrupted file.

### Q18: What is stale health detection?
**Answer:** If the health monitor process crashes or stops updating, the timestamp in `health_status.json` ages. The client checks `time.time() - updated_at`: if older than `stale_health_threshold_sec` (15s), the data is deemed stale, a warning is logged, and the client falls back to default priority ordering.

### Q19: Describe the step-by-step failover process when Resolver A fails.
**Answer:**
1. Client consults selector; Resolver A is chosen as primary.
2. Client sends UDP query to Resolver A.
3. Socket timer elapses (`socket.timeout`).
4. Client logs warning and immediately attempts the next candidate in the fallback sequence (Resolver B).
5. Resolver B answers; client caches result and sets `failover_occurred = True`.
6. Concurrently, Health Monitor records missed PINGs, crosses failure threshold, and updates JSON to mark Resolver A OFFLINE.

### Q20: How does recovery re-entry take place?
**Answer:** When Resolver A is rebooted, the Health Monitor detects consecutive PONG replies and marks Resolver A ONLINE in `health_status.json`. On subsequent queries, the Resolver Selector detects Resolver A's restored status and automatically resumes routing traffic to it based on its priority or latency ranking.

### Q21: What metrics does the health monitor compute over time?
**Answer:** Availability state (boolean), instantaneous round-trip latency (`latency_ms`), consecutive failure/success counts, total probes dispatched, successful probes received, and packet loss percentage (`packet_loss_percent`).

---

## Category 4: Load Balancing Policies (Questions 22–27)

### Q22: What load balancing policies are supported in this system?
**Answer:**
1. `lowest_latency`: Selects the healthy resolver with the lowest measured round-trip time.
2. `round_robin`: Cycles sequentially among healthy resolvers.
3. `priority`: Enforces static preference order (Resolver A rank 1, Resolver B rank 2).
4. `random`: Uniformly selects randomly among healthy resolvers.

### Q23: Why is lowest-latency balancing preferred over simple round-robin in DNS?
**Answer:** In heterogeneous or geographically distributed networks, resolvers exhibit different processing capacities and link latencies. Lowest-latency routing ensures queries are directed to the resolver capable of fulfilling them fastest, minimizing total user lookup latency.

### Q24: What happens if all resolvers are marked OFFLINE in the health status file?
**Answer:** The selector enters emergency fallback mode: it issues a critical warning and attempts all resolvers in configured priority order regardless of reported health status. This protects against false outages caused by monitor process failures.

### Q25: How is round-robin state maintained across queries?
**Answer:** The `ResolverSelector` maintains an internal index counter protected by a threading lock. Each call increments the index modulo the number of currently healthy servers (`index = (index + 1) % len(healthy)`).

### Q26: Can a client change its load balancing policy dynamically?
**Answer:** Yes. In interactive mode, typing `policy` toggles policies on the fly. Programmatically or via CLI, passing `--policy <name>` overrides the default configuration without restarting any service.

### Q27: How does the client explain its selection decision in the terminal?
**Answer:** Every resolution returns an `explanation` string documenting the rationale, e.g.:
`"Selected Resolver A (10.0.0.20:5000) based on lowest measured latency (1.25 ms) under policy 'lowest_latency'."`

---

## Category 5: Software-Defined Networking & OpenFlow 1.3 (Questions 28–36)

### Q28: What is Software-Defined Networking (SDN)?
**Answer:** SDN is a network architecture paradigm that decouples the network control plane (decision-making logic) from the data forwarding plane (underlying switches and routers). A centralized software controller programs forwarding devices via standardized protocols such as OpenFlow.

### Q29: What is OpenFlow 1.3, and how does its flow table pipeline operate?
**Answer:** OpenFlow 1.3 is an open interface standard connecting SDN controllers and switches. Switches maintain one or more Flow Tables containing prioritized Flow Entries. Each entry specifies:
- **Match Fields:** Ingress port, Ethernet type, IP protocol, IP addresses, UDP ports.
- **Priority:** Higher numbers evaluated first.
- **Counters:** Packets and bytes matched.
- **Instructions/Actions:** Forward to port, drop, push/pop VLAN, send to controller (`OFPP_CONTROLLER`).
- **Timeouts:** `idle_timeout` and `hard_timeout`.

### Q30: What is a Table-Miss Flow Entry?
**Answer:** A default entry installed at Priority 0 with an empty match field. When an incoming packet matches no higher-priority rule, the table-miss entry dictates the fallback behavior—typically forwarding the packet header to the controller via a `Packet-In` message.

### Q31: How does your SDN controller identify DNS traffic?
**Answer:** The controller inspects frame headers for:
`eth_type = 0x0800` (IPv4) AND `ip_proto = 17` (UDP) AND `udp_dst in [5000, 5001, 53]`.

### Q32: What specific OpenFlow rules does your controller install for DNS?
**Answer:** When DNS traffic is identified, the controller pushes a proactive flow mod at **Priority 100** matching client ingress port (`in_port=1`) and target UDP port (`udp_dst=5000/5001`), with action `OUTPUT: target_resolver_port` (port 2 for Resolver A, or port 3 for Resolver B).

### Q33: How does the SDN controller implement dynamic traffic redirection on failover?
**Answer:** The controller continuously monitors `health_status.json`. When Resolver A fails, the controller executes a dynamic flow modification: it installs a high-priority override rule (**Priority 200**) that intercepts DNS traffic and steers it to Switch Port 3 (Resolver B).

### Q34: What is the crucial difference between application-level selection and network-level SDN forwarding?
**Answer:**
- **Application-Level:** The client software selects the IP destination in the socket packet header. If the client lacks failover logic, failure at the server breaks resolution.
- **Network-Level (SDN):** Open vSwitch inspects packets on the wire and enforces routing policies via OpenFlow flow tables. The SDN controller can reroute, load-balance, or mirror traffic at the switch level completely transparently to the client.

### Q35: How does the controller collect port telemetry statistics?
**Answer:** The controller periodically dispatches `OFPPortStatsRequest` messages to switch `s1`. The switch responds with `OFPPortStatsReply` containing cumulative `rx_packets`, `tx_packets`, `rx_bytes`, and `tx_bytes` per switch port.

### Q36: What is Ryu / OS-Ken?
**Answer:** Ryu is a component-based Software-Defined Networking framework providing software APIs for OpenFlow 1.0 through 1.5. `os-ken` is the community-maintained, modern fork of Ryu optimized for Python 3.10, 3.11, and 3.12.

---

## Category 6: Mininet & Virtual Switching (Questions 37–40)

### Q37: What is Mininet, and how does it emulate networks?
**Answer:** Mininet is a network emulator that creates a virtual OpenFlow network on a single Linux kernel using OS-level virtualization: Linux Network Namespaces for isolated hosts, virtual ethernet pairs (`veth`) for links, and Open vSwitch for software switching.

### Q38: What is Open vSwitch (OVS)?
**Answer:** Open vSwitch is a production-quality, open-source multilayer virtual switch designed to enable network automation through programmatic extensions while supporting standard management interfaces and OpenFlow protocols.

### Q39: Why can't we use 127.0.0.1 for host-to-host communication in Mininet?
**Answer:** In Mininet, each host has its own private network namespace with an independent loopback interface. Sending to `127.0.0.1` inside `h1` routes packets to `h1`'s local loopback, never traversing the virtual switch or reaching `h2`/`h3`. Hosts must communicate using their assigned virtual subnet IP addresses (`10.0.0.10`, `10.0.0.20`, `10.0.0.30`).

### Q40: What does `sudo mn -c` do?
**Answer:** It performs a full Mininet cleanup: removing leftover Open vSwitch bridges, terminating zombie controller or host processes, flushing virtual ethernet (`veth`) interfaces, and deleting temporary files in `/tmp`.

---

## Category 7: Performance Evaluation & Benchmarking (Questions 41–45)

### Q41: How is throughput (QPS) measured in your benchmark suite?
**Answer:** The benchmark executes a fixed batch of resolution queries across multiple concurrent worker threads (1, 5, 10, 20 threads) using `ThreadPoolExecutor`. Throughput is calculated as:
$$\text{QPS} = \frac{\text{Total Queries Completed}}{\text{Wall Clock Elapsed Seconds}}$$

### Q42: What speedup factor does client-side caching achieve in empirical tests?
**Answer:** In empirical benchmarks, network UDP round-trips require 1.0 to 3.0 ms, whereas local in-memory cache lookups complete in 0.02 to 0.04 ms. This yields an acceleration factor of **30x to 80x speedup**.

### Q43: How is the failover latency penalty quantified?
**Answer:** During normal operation, query latency hovers around ~1.2 ms. During a failover event, the client incurs a socket timeout delay (e.g. 1.0s) waiting for Resolver A before querying Resolver B. Once the health monitor marks Resolver A offline, subsequent queries immediately route to Resolver B, stabilizing latency back to ~1.4 ms.

### Q44: What are the primary CSV files and Matplotlib plots produced?
**Answer:**
1. `latency_comparison.csv` -> `resolver_latency_comparison.png`
2. `cache_performance.csv` -> `cache_hit_vs_miss.png`
3. `failover_timeline.csv` -> `failover_performance.png`
4. `throughput_benchmark.csv` -> `throughput_analysis.png`
5. `resolver_availability.csv` -> `resolver_availability.png`
6. `system_summary_dashboard.png` (Comprehensive 2x2 dashboard)

### Q45: How can this system be extended for future academic work?
**Answer:** Future enhancements include:
1. Implementing DNSSEC signature verification.
2. Migrating to DNS-over-HTTPS (DoH) or DNS-over-TLS (DoT).
3. Integrating machine-learning-based predictive latency routing.
4. Expanding to multi-switch fat-tree data center topologies.
