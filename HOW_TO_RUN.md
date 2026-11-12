# How to Run the DNS-SDN Resolution System

This guide provides simple, copy-pasteable commands to run the project in any environment.

---

## 🚀 Mode 1: Fast Start (Localhost Mode)
*Works on **macOS**, **Linux**, and **Ubuntu** without requiring root or Mininet.*

### Step 1: Start All Background Services
In your terminal, start the SDN Controller, Resolver A (port 5000), Resolver B (port 5001), and the Health Monitor:
```bash
./scripts/start_project.sh
```
*(All 4 background services will launch and display their Process IDs).*

### Step 2: Run the DNS Client
Open a second terminal window (or run in the same terminal):
```bash
python3 client/client.py --local
```
**Try these interactive queries:**
- Type `server1.local` -> Resolves to `192.0.2.10` from Resolver A (Cache Miss)
- Type `server1.local` again -> Resolves in **0.03 ms** (Cache Hit!)
- Type `invalid.domain` -> Returns `NOT_FOUND` (Negative Cache Hit!)
- Type `policy` -> Toggles between `lowest_latency`, `round_robin`, and `priority`
- Type `stats` -> Displays live cache hits, misses, and hit-ratio %
- Type `exit` -> Quits the client

### Step 3: Launch the Real-Time Web Dashboard (Optional)
In another terminal:
```bash
streamlit run dashboard/app.py
```
*Opens a live browser dashboard at `http://localhost:8501` showing real-time server health, latency gauges, traffic distribution, and an interactive query tool.*

### Step 4: Stop Everything Safely
When finished:
```bash
./scripts/stop_project.sh
```

---

## 🌐 Mode 2: Full Mininet & SDN OpenFlow 1.3 Emulation
*Requires **Ubuntu Linux** with Mininet and Open vSwitch installed.*

### Step 1: Install System Dependencies (First time only)
```bash
chmod +x scripts/*.sh
./scripts/install.sh
```

### Step 2: Start the SDN OpenFlow Controller
In **Terminal 1**:
```bash
# Using Ryu / OS-Ken:
osken-manager sdn/sdn_controller.py

# Or using the built-in standalone engine:
python3 sdn/sdn_controller.py --standalone
```
*The controller will listen on TCP port 6653.*

### Step 3: Start the Mininet Topology
In **Terminal 2**:
```bash
sudo python3 mininet/mininet_topology.py --auto-start
```
*This sets up switch `s1`, starts Resolver A inside `h2` (`10.0.0.20:5000`), starts Resolver B inside `h3` (`10.0.0.30:5001`), and drops you into the `mininet>` CLI.*

### Step 4: Run Queries from the Client Host (`h1`)
Inside the `mininet>` prompt:
```bash
# 1. Normal resolution from client h1
mininet> h1 python3 client/client.py --hostname server1.local

# 2. Test cache hit speedup
mininet> h1 python3 client/client.py --hostname server1.local

# 3. Test load-balancing policy
mininet> h1 python3 client/client.py --hostname server2.local --policy round_robin

# 4. Simulate server failure: kill Resolver A on h2
mininet> h2 pkill -f resolver.py

# 5. Query again from h1 (Client automatically fails over to Resolver B!)
mininet> h1 python3 client/client.py --hostname database.local
```

### Step 5: Exit and Clean Up
```bash
mininet> exit
./scripts/stop_project.sh
```

---

## 🧪 Running Automated Tests
Run all 25 unit and integration tests (verifying all 12 specification requirements):
```bash
pytest tests/ -v
```
*All 25 tests will run and report `PASSED`.*

---

## 📈 Running Performance Benchmarks
Run empirical workloads and generate the 6 Matplotlib charts in `results/`:
```bash
./scripts/run_benchmarks.sh
```
View the generated charts in the `results/` folder:
- `results/system_summary_dashboard.png`
- `results/cache_hit_vs_miss.png`
- `results/failover_performance.png`
- `results/throughput_analysis.png`
- `results/resolver_latency_comparison.png`
- `results/resolver_availability.png`

---

## 📋 Common Troubleshooting

| Issue | Solution |
|---|---|
| **Port 5000 / 5001 already in use** | Run `./scripts/stop_project.sh` or `pkill -f resolver.py` |
| **Mininet network already exists** | Run `sudo mn -c` |
| **Permission denied on scripts** | Run `chmod +x scripts/*.sh` |
| **Health file stale warning** | Ensure `monitoring/health_monitor.py` is running |

