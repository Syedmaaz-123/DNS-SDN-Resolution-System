# ⚡ Quick Demo Cheat Sheet & Hostname Reference

---

## 1. Quick Terminal Commands to Start & Run

### Terminal 1: Start All Services
```bash
./scripts/start_project.sh
```

### Terminal 2: Run the DNS Client
```bash
python3 client/client.py --local
```

### Terminal 3 (Optional): Open the Web Dashboard
```bash
streamlit run dashboard/app.py
```

### When Finished: Stop Everything
```bash
./scripts/stop_project.sh
```

---

## 2. Complete Hostname Database Table

All hostnames configured in `resolver/dns_records.json`:

| # | Hostname to Type | Resolved IP Address | System Role | Expected Output |
|---|---|---|---|---|
| 1 | **`server1.local`** | `192.0.2.10` | Primary Web Server | `OK 192.0.2.10` |
| 2 | **`server2.local`** | `192.0.2.20` | Secondary App Server | `OK 192.0.2.20` |
| 3 | **`database.local`** | `192.0.2.40` | Main SQL Database | `OK 192.0.2.40` |
| 4 | **`college.local`** | `192.0.2.50` | University Portal | `OK 192.0.2.50` |
| 5 | **`printer.local`** | `192.0.2.30` | Network Printer | `OK 192.0.2.30` |
| 6 | **`web.local`** | `192.0.2.60` | HTTP Web Host | `OK 192.0.2.60` |
| 7 | **`mail.local`** | `192.0.2.70` | SMTP Mail Server | `OK 192.0.2.70` |
| 8 | **`gateway.local`** | `192.0.2.1` | Network Gateway Router | `OK 192.0.2.1` |
| 9 | **`vpn.local`** | `192.0.2.80` | Remote Access VPN | `OK 192.0.2.80` |
| 10 | **`api.local`** | `192.0.2.90` | REST API Service | `OK 192.0.2.90` |

---

## 3. Negative Cache Test Hostnames (Invalid Domains)

Type any domain not listed above to demonstrate **Negative Caching (RFC 2308)**:

| Hostname to Type | Result First Time | Result Second Time (Negative Hit) |
|---|---|---|
| **`fake.local`** | `NOT_FOUND` (cached for 30s) | `[NEGATIVE CACHE HIT]` (instant, 0.02 ms) |
| **`test.com`** | `NOT_FOUND` (cached for 30s) | `[NEGATIVE CACHE HIT]` (instant, 0.02 ms) |
| **`unknown.domain`** | `NOT_FOUND` (cached for 30s) | `[NEGATIVE CACHE HIT]` (instant, 0.02 ms) |

---

## 4. Special Control Commands

Type these directly into the client prompt:

| Command | Action | What to Look For |
|---|---|---|
| **`stats`** | View live cache metrics | Shows total hits, misses, hit-ratio %, active entries |
| **`policy`** | Toggle load balancing policy | Switches: `lowest_latency` ➔ `round_robin` ➔ `priority` |
| **`flush`** | Clear client DNS cache | Removes cached records so you can re-test network misses |
| **`exit`** | Exit client application | Closes prompt cleanly |

---

## 5. 5-Step Demo Script for Examiners & Viva

Follow these 5 steps in order during your evaluation:

1. **Step 1: Normal Query & Cache Miss**  
   Type: `server1.local`  
   *Point out:* Resolved via Resolver A in **~1.2 ms** (Network query).

2. **Step 2: Instant Cache Acceleration**  
   Type: `server1.local` again  
   *Point out:* **`[CACHE HIT]`** in **0.03 ms** (**~50x faster** than network!).

3. **Step 3: Negative Caching (RFC 2308)**  
   Type: `fake.local`  
   *Point out:* Shows `NOT_FOUND`. Type it again to show **`[NEGATIVE CACHE HIT]`**.

4. **Step 4: Load Balancing Policy Switch**  
   Type: `policy` (switches to `round_robin`).  
   Type: `database.local` then `printer.local`.  
   *Point out:* Queries alternate between Resolver A and Resolver B.

5. **Step 5: Automatic Server Failover Demo**  
   In another terminal, stop Resolver A: `pkill -f "port 5000"`.  
   In client, type: `college.local`.  
   *Point out:* Client automatically detects timeout and **fails over to Resolver B** with zero interruption!

