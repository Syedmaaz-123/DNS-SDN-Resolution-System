# System Architecture & Technical Design Specification

**Project Title:** DNS-SDN Resolution System: Intelligent DNS-like Resolution with Multiple Resolvers, Dynamic Load Balancing, Fault Tolerance and SDN-Controlled Network Forwarding
**Version:** 2.0.0 (Academic Edition)
**Standard:** OpenFlow 1.3 / IEEE UDP DNS Model

---

## 1. High-Level System Architecture

The DNS-SDN Resolution System combines **Application-Level Intelligence** (client-side positive/negative caching, latency ranking, failover handling) with **Network-Level Programmability** (OpenFlow 1.3 flow table modification, packet inspection, dynamic traffic steering).

```
+-----------------------------------------------------------------------------------+
|                              SDN CONTROL PLANE                                    |
|                                                                                   |
|   +---------------------------------------------------------------------------+   |
|   |             Ryu / OS-Ken OpenFlow 1.3 Controller Engine                   |   |
|   |  - Table-Miss Flow Management        - MAC Learning & L2 Switching        |   |
|   |  - DNS Priority Flow Installation    - Dynamic Failover Redirection       |   |
|   |  - Periodic Port Telemetry Polling   - Live Network Metrics JSON Exporter |   |
|   +---------------------------------------------------------------------------+   |
+------------------------------------------^----------------------------------------+
                                           | OpenFlow 1.3 (TCP Port 6653)
                                           v
+-----------------------------------------------------------------------------------+
|                              SDN DATA PLANE (Mininet)                             |
|                                                                                   |
|                                +-------------------+                              |
|                                |   Open vSwitch    |                              |
|                                |       (s1)        |                              |
|                                +---+-----+-----+---+                              |
|                      Port 1 (eth1) |     |     | Port 3 (eth3)                    |
|                                    |     | Port 2 (eth2)                          |
|             +----------------------+     |     +----------------------+           |
|             |                            |                            |           |
|             v                            v                            v           |
|      +--------------+             +--------------+             +--------------+   |
|      |   Host h1    |             |   Host h2    |             |   Host h3    |   |
|      |  10.0.0.10   |             |  10.0.0.20   |             |  10.0.0.30   |   |
|      | (DNS Client) |             |(Resolver A)  |             |(Resolver B)  |   |
|      | UDP Port Ephem             |UDP Port 5000 |             |UDP Port 5001 |   |
|      +--------------+             +--------------+             +--------------+   |
+-----------------------------------------------------------------------------------+
```

---

## 2. Mininet Network Topology

The network consists of a single Open vSwitch (`s1`) interconnected with three virtual Linux network namespace hosts:

```mermaid
graph TD
    c0["SDN Controller (c0)<br/>127.0.0.1:6653<br/>OpenFlow 1.3"]
    s1["OpenFlow Switch (s1)<br/>Open vSwitch"]
    h1["Client Host (h1)<br/>10.0.0.10/24<br/>MAC: 00:00:00:00:00:01"]
    h2["Resolver A (h2)<br/>10.0.0.20/24<br/>MAC: 00:00:00:00:00:02<br/>Port: 5000"]
    h3["Resolver B (h3)<br/>10.0.0.30/24<br/>MAC: 00:00:00:00:00:03<br/>Port: 5001"]

    c0 <== "OpenFlow 1.3 Channel" ==> s1
    s1 ---|"Port 1"| h1
    s1 ---|"Port 2"| h2
    s1 ---|"Port 3"| h3
```

### Addressing Schema

| Node         | Interface       | IP Address         | MAC Address                       | Role                    | Switch Port |
| ------------ | --------------- | ------------------ | --------------------------------- | ----------------------- | ----------- |
| **h1** | `h1-eth0`     | `10.0.0.10/24`   | `00:00:00:00:00:01`             | DNS Resolution Client   | Port 1      |
| **h2** | `h2-eth0`     | `10.0.0.20/24`   | `00:00:00:00:00:02`             | Resolver Server A       | Port 2      |
| **h3** | `h3-eth0`     | `10.0.0.30/24`   | `00:00:00:00:00:03`             | Resolver Server B       | Port 3      |
| **s1** | `s1-eth[1-3]` | None (L2/L3)       | Virtual DPID `0000000000000001` | OpenFlow 1.3 Switch     | -           |
| **c0** | Remote          | `127.0.0.1:6653` | N/A                               | Ryu / OS-Ken Controller | -           |

---

## 3. Communication Workflows

# 3.1 Client Resolution Workflow (with Caching & Load Balancing)

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant Client as DNS Client (h1)
    participant Cache as DNS Cache
    participant Selector as Resolver Selector
    participant HM as Health Monitor
    participant SrvA as Resolver A (h2)
    participant SrvB as Resolver B (h3)

    User->>Client: Input hostname (e.g. server1.local)
    Client->>Cache: Check hostname in cache
    alt Positive Cache Hit
        Cache-->>Client: Return IP (192.0.2.10, Remaining TTL)
        Client-->>User: Display Cached IP (Latency < 0.1 ms)
    else Negative Cache Hit
        Cache-->>Client: Return NOT_FOUND (Remaining Negative TTL)
        Client-->>User: Display NOT_FOUND immediately
    else Cache Miss
        Client->>Selector: Request optimal resolver order
        Selector->>HM: Read health_status.json
        HM-->>Selector: Server health, latency, & availability
        Selector-->>Client: Selected: Resolver A (Lowest Latency 1.25 ms)
      
        Client->>SrvA: UDP: RESOLVE server1.local
        alt Resolver A Responds OK
            SrvA-->>Client: UDP: OK 192.0.2.10
            Client->>Cache: Store Positive Entry (TTL=100s)
            Client-->>User: Display Resolved IP & Latency
        else Resolver A Times Out
            Note over Client,SrvB: AUTOMATIC FAILOVER TRIGGERED
            Client->>SrvB: UDP: RESOLVE server1.local
            SrvB-->>Client: UDP: OK 192.0.2.10
            Client->>Cache: Store Positive Entry (TTL=100s)
            Client-->>User: Display Resolved via Failover to Resolver B
        end
    end
```

---

### 3.2 Periodic Health Monitoring & Flapping Mitigation

```mermaid
sequenceDiagram
    autonumber
    participant HM as Health Monitor Daemon
    participant SrvA as Resolver A (Port 5000)
    participant SrvB as Resolver B (Port 5001)
    participant Status as health_status.json (Atomic)

    loop Every 3.0 Seconds
        HM->>SrvA: UDP PING
        alt PONG received
            SrvA-->>HM: UDP PONG (RTT = 1.2 ms)
            HM->>HM: Increment consecutive_successes, reset failures
        else Timeout (1.5s)
            HM->>HM: Increment consecutive_failures
            opt failures >= failure_threshold (2)
                HM->>HM: Mark Resolver A OFFLINE
            end
        end

        HM->>SrvB: UDP PING
        SrvB-->>HM: UDP PONG (RTT = 1.4 ms)

        HM->>Status: Atomic Write via .tmp rename
    end
```

---

### 3.3 SDN Controller Dynamic Forwarding & OpenFlow Flow Pipeline

```mermaid
sequenceDiagram
    autonumber
    participant Switch as Open vSwitch (s1)
    participant Controller as Ryu SDN Controller
    participant Health as health_status.json
    participant FlowMgr as Flow Manager

    Switch->>Controller: OFPFeaturesReply (Switch Connected)
    Controller->>Switch: OFPFlowMod (Priority 0: Table-Miss -> Send to Controller)
  
    loop Dynamic Telemetry & Failover Loop (Every 5s)
        Controller->>Health: Inspect Resolver Health
        alt Resolver A is Healthy
            Controller->>FlowMgr: Target Port = 2 (Resolver A)
        else Resolver A Failed
            Controller->>FlowMgr: Target Port = 3 (Resolver B)
            Controller->>Switch: OFPFlowMod (Priority 200: UDP 5000/5001 -> Port 3)
            Note over Controller,Switch: OpenFlow Rule Dynamically Steers Traffic!
        end
        Controller->>Switch: OFPPortStatsRequest
        Switch-->>Controller: OFPPortStatsReply (RX/TX packets & bytes)
        Controller->>Controller: Export sdn_stats.json
    end
```

---

## 4. Fundamental Architectural Distinction

### Application-Level Selection vs. Network-Level SDN Forwarding

In classical networking, name resolution and routing are decoupled. This project demonstrates how Software-Defined Networking integrates them:

1. **Application-Level Selection (Client Tier):**

   - **Layer:** OSI Layer 7 (Application).
   - **Mechanism:** The client socket application actively chooses whether to send a packet to socket `10.0.0.20:5000` or `10.0.0.30:5001`.
   - **Control Variables:** In-memory caching, user-specified balancing policies (`lowest_latency`, `round_robin`), and reading `health_status.json`.
   - **Limitation:** If a client application has no built-in failover, a server outage halts queries entirely.
2. **Network-Level Forwarding (SDN Control & Data Tier):**

   - **Layer:** OSI Layer 2 (Data Link), Layer 3 (Network), and Layer 4 (Transport).
   - **Mechanism:** Open vSwitch inspects incoming packet headers (`eth_type=0x0800`, `ip_proto=17`, `udp_dst=5000/5001`).
   - **Control Variables:** OpenFlow 1.3 match-action tables pushed by the Ryu/OS-Ken controller.
   - **Advantage:** The SDN controller can dynamically rewrite packet destination addresses or redirect forwarding ports directly at switch hardware line rate, providing transparent failover and network-enforced load balancing without modifying end-host application code!
