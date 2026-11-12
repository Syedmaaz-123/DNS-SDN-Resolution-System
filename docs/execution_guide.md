# Step-by-Step Execution & Demonstration Guide

This guide is designed for students and researchers to confidently execute, demonstrate, and defend the DNS-SDN Resolution System in an academic laboratory or presentation setting.

---

## 1. Execution Modalities Overview

The project supports two operational modes:

| Mode | Environment | Description |
|---|---|---|
| **Mode A: Mininet SDN Topology** | Ubuntu Linux with Root / sudo | Full virtualized OpenFlow 1.3 switch (`s1`) with isolated network namespaces (`h1`, `h2`, `h3`) and remote controller (`c0`). |
| **Mode B: Local Process Emulation** | Linux / macOS / Non-root | Runs all components via loopback sockets (`127.0.0.1:5000` & `5001`), with identical logic, caching, failover, and telemetry. |

---

## 2. Fast Track: Single-Command Automated Demonstration

If you need to quickly launch the demonstration during a viva or presentation:

```bash
# Terminal 1: Launch all background services (Controller, Resolvers, Health Monitor)
./scripts/start_project.sh

# Terminal 2: Run interactive DNS client
python3 client/client.py --local

# Terminal 3 (Optional): Launch real-time web dashboard
streamlit run dashboard/app.py

# When finished:
./scripts/stop_project.sh
```

---

## 3. Complete Step-by-Step Academic Walkthrough (Mininet & SDN)

Follow this 21-step procedure to demonstrate each component individually:

### [Step 1-7] Environment & Dependency Verification
Open a fresh Ubuntu terminal:
```bash
# Verify Python version (3.10+)
python3 --version

# Verify Mininet and OVS
sudo mn --version
sudo ovs-vsctl --version

# Run test suite
pytest tests/ -v
```

---

### [Step 8] Start the SDN Controller
Open **Terminal 1 (SDN Controller Terminal)**:
```bash
# Run with Ryu or OS-Ken:
osken-manager sdn/sdn_controller.py
# (Or using the built-in standalone engine):
python3 sdn/sdn_controller.py --standalone
```
*Expected Output:*
```
=================================================================
       SDN OPENFLOW 1.3 CONTROLLER (STANDALONE ENGINE)
=================================================================
  Listening on        : 0.0.0.0:6653
  Protocol            : OpenFlow 1.3 (Wire Version 0x04)
  Active Resolver Port: Port 2 (Resolver A)
  Stats Output        : sdn/sdn_stats.json
=================================================================
```

---

### [Step 9] Start the Mininet Network Topology
Open **Terminal 2 (Mininet Terminal)**:
```bash
sudo python3 mininet/mininet_topology.py --cli
```
*Expected Output:*
```
*** Starting Network & OpenFlow Switch (s1)...
============================================================
  DNS-SDN MININET NETWORK READY
  h1 (Client)     : IP=10.0.0.10 MAC=00:00:00:00:00:01 Connected to s1 port 1
  h2 (Resolver A) : IP=10.0.0.20 MAC=00:00:00:00:00:02 Connected to s1 port 2
  h3 (Resolver B) : IP=10.0.0.30 MAC=00:00:00:00:00:03 Connected to s1 port 3
  Controller      : 127.0.0.1:6653 (OpenFlow 1.3)
============================================================
mininet>
```

---

### [Step 10] Start Resolver A inside Host h2
Inside the **Mininet CLI (`mininet>`)**:
```bash
mininet> h2 python3 resolver/resolver.py --name "Resolver A" --host 10.0.0.20 --port 5000 > logs/resolver_a.log 2>&1 &
```

---

### [Step 11] Start Resolver B inside Host h3
Inside the **Mininet CLI (`mininet>`)**:
```bash
mininet> h3 python3 resolver/resolver.py --name "Resolver B" --host 10.0.0.30 --port 5001 > logs/resolver_b.log 2>&1 &
```

---

### [Step 12] Start Health Monitoring inside Host h1
Inside the **Mininet CLI (`mininet>`)**:
```bash
mininet> h1 python3 monitoring/health_monitor.py > logs/health_monitor.log 2>&1 &
```

---

### [Step 13-14] Start DNS Client and Perform Normal Resolution
Inside the **Mininet CLI (`mininet>`)**:
```bash
mininet> h1 python3 client/client.py --hostname server1.local
```
*Expected Output:*
```
[CACHE MISS]
[SELECTOR] Selected Resolver A (10.0.0.20:5000) based on lowest measured latency (1.25 ms).
  Tried Resolver A (10.0.0.20:5000) -> SUCCESS (1.25 ms)

Resolved using Resolver A
Resolved IP: 192.0.2.10
Cached for 100.0 seconds.
Response time: 1.250 ms
Total lookup time: 1.380 ms
```

---

### [Step 15] Test Positive Caching
Run the same command immediately:
```bash
mininet> h1 python3 client/client.py --hostname server1.local
```
*Expected Output:*
```
[CACHE HIT] Valid for 98.42 seconds
Hostname: server1.local
IP Address: 192.0.2.10
Total lookup time: 0.035 ms  <-- 30x faster!
```

---

### [Step 16] Test Negative Caching (Non-Existent Host)
Query an unknown hostname:
```bash
mininet> h1 python3 client/client.py --hostname invalid.domain.xyz
```
*Expected Output:*
```
Resolved using Resolver A
Hostname does not exist.
Cached negative entry for 30.0 seconds.
```
Repeat the query to show negative cache hit:
```bash
mininet> h1 python3 client/client.py --hostname invalid.domain.xyz
```
*Expected Output:*
```
[NEGATIVE CACHE HIT] Hostname known not to exist (TTL remaining: 28.10s)
```

---

### [Step 17] Test Load Balancing (Round-Robin vs Lowest Latency)
Test round-robin policy:
```bash
mininet> h1 python3 client/client.py --hostname server2.local --policy round_robin
mininet> h1 python3 client/client.py --hostname printer.local --policy round_robin
```
*Notice how queries alternate sequentially between Resolver A and Resolver B.*

---

### [Step 18] Demonstrate Automatic Failover (Simulating Resolver A Outage)
Kill Resolver A on `h2`:
```bash
mininet> h2 pkill -f resolver.py
```
Wait 3 seconds for the Health Monitor to detect the failure. Then resolve from `h1`:
```bash
mininet> h1 python3 client/client.py --hostname database.local
```
*Expected Output:*
```
Query to Resolver A (10.0.0.20:5000) timed out. Trying next resolver...
[OPENFLOW FAILOVER] Packet steered to Resolver B on switch port 3.

Resolved using Resolver B
Resolved IP: 192.0.2.40
Failover occurred: True
```

---

### [Step 19] Demonstrate Resolver Recovery
Restart Resolver A on `h2`:
```bash
mininet> h2 python3 resolver/resolver.py --name "Resolver A" --host 10.0.0.20 --port 5000 > logs/resolver_a.log 2>&1 &
```
Within 3 seconds, Health Monitor reports:
```
[RECOVERY] Resolver A recovered after 2 consecutive successful checks!
```
Now run query again from `h1`:
```bash
mininet> h1 python3 client/client.py --hostname college.local
```
*Resolver A automatically handles the query again!*

---

### [Step 20] Execute Benchmarks and View Generated Charts
In an external Ubuntu terminal:
```bash
./scripts/run_benchmarks.sh
```
Open `results/` to view the 6 generated Matplotlib figures:
```bash
xdg-open results/system_summary_dashboard.png
```

---

### [Step 21] Safe Shutdown of All Components
Exit the Mininet CLI:
```bash
mininet> exit
```
Then run the automated cleanup script:
```bash
./scripts/stop_project.sh
```
*This terminates all background processes and cleans up Open vSwitch flow tables (`sudo mn -c`).*

