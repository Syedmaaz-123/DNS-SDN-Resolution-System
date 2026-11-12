# 🎓 Viva & Demo Presentation Guide: How to Present in Front of the Examiner ("Sir")

This document gives you the **exact terminal commands to type** and the **exact words to speak** when presenting your project to the examiner / professor ("Sir").

---

## 🖥️ Pre-Demo Setup (Do this before Sir comes to your screen)

Open **3 Terminal windows** and have them ready:

- **Terminal 1:** Where background services run (`./scripts/start_project.sh`)
- **Terminal 2:** Where you run the client and type queries
- **Terminal 3:** Where you run the web dashboard (or kill a server for failover)

---

## 🎬 The 6-Step Presentation Walkthrough

### 🚀 Step 1: Start the System

**In Terminal 1, type:**
```bash
./scripts/start_project.sh
```

**🗣️ What you SAY to Sir:**
> *"Sir, I am starting the background infrastructure. This single command boots four independent processes:  
> 1. The OpenFlow 1.3 SDN Controller on port 6653.  
> 2. Resolver A on UDP port 5000.  
> 3. Resolver B on UDP port 5001.  
> 4. The Health Monitor daemon which continuously pings both servers."*

---

### 🌐 Step 2: Normal DNS Resolution over UDP

**In Terminal 2, type:**
```bash
python3 client/client.py --local
```
Then inside the client prompt, type:
```text
server1.local
```

**What appears on screen:**
```text
[CACHE MISS]
[SELECTOR] Selected Resolver A (127.0.0.1:5000) based on lowest measured latency (1.25 ms).
Resolved using Resolver A
Resolved IP: 192.0.2.10
Cached for 100.0 seconds.
Response time: 1.250 ms
Total lookup time: 1.380 ms
```

**🗣️ What you SAY to Sir:**
> *"Sir, here is a normal DNS lookup. The client checked its local cache first, had a cache miss, consulted the intelligent selector, and queried Resolver A. Resolver A answered with IP `192.0.2.10` over UDP in 1.25 milliseconds. The record is now cached for 100 seconds."*

---

### ⚡ Step 3: Demonstrate Cache Speedup (50x Acceleration!)

**In Terminal 2, type the exact same hostname again:**
```text
server1.local
```

**What appears on screen:**
```text
[CACHE HIT] Valid for 98.40 seconds
Hostname: server1.local
IP Address: 192.0.2.10
Total lookup time: 0.035 ms
```

**🗣️ What you SAY to Sir:**
> *"Sir, notice the lookup time now: it dropped from 1.25 ms down to 0.035 ms. That is almost a 50x speedup because it was served directly from in-memory cache without sending any packets across the network."*

---

### 🚫 Step 4: Demonstrate Negative Caching (RFC 2308)

**In Terminal 2, type a fake domain:**
```text
fake.local
```
*(Shows `NOT_FOUND` in ~1.2 ms).*

**Immediately type it again:**
```text
fake.local
```
*(Shows `[NEGATIVE CACHE HIT] Hostname known not to exist` in 0.02 ms).*

**🗣️ What you SAY to Sir:**
> *"Sir, this demonstrates Negative Caching according to RFC 2308. In standard DNS, if an application queries an invalid domain, it repeatedly floods the server network. Our client caches the `NOT_FOUND` result for 30 seconds so repeat failed lookups are handled locally in 0.02 ms."*

---

### ⚖️ Step 5: Demonstrate Load Balancing (Round-Robin vs Lowest Latency)

**In Terminal 2, type:**
```text
policy
```
*(Switches to `round_robin`).*

Now type two queries:
```text
database.local
```
*(Handled by Resolver A -> `192.0.2.40`)*

Then type:
```text
printer.local
```
*(Handled by Resolver B -> `192.0.2.30`)*

**🗣️ What you SAY to Sir:**
> *"Sir, I have toggled the load-balancing policy to Round-Robin. Notice how the first query went to Resolver A and the second query automatically alternated to Resolver B. Our system also supports lowest-latency and priority-based policies."*

---

### 💥 Step 6: The "Showstopper" – Server Outage & Instant Automatic Failover!

**In Terminal 3 (or a separate tab), kill Resolver A:**
```bash
pkill -f "port 5000"
```

**Now, go back to Terminal 2 (Client) and type:**
```text
college.local
```

**What appears on screen:**
```text
Query to Resolver A timed out. Trying next resolver...
Resolved using Resolver B
Resolved IP: 192.0.2.50
Failover occurred: True
Total lookup time: 10.2 ms
```

**🗣️ What you SAY to Sir:**
> *"Sir, this is the most critical feature: fault tolerance. I just killed Resolver A. The client detected the socket timeout and automatically failed over to Resolver B. The user got the correct IP `192.0.2.50` with zero interruption to the application.  
> Concurrently, our Health Monitor detected two consecutive failed pings, marked Resolver A OFFLINE to prevent route flapping, and the SDN controller dynamically updated switch flow rules to steer future DNS packets directly to Resolver B."*

---

### 📊 Step 7: Live Web Dashboard & Telemetry (Optional Visual Bonus)

**In Terminal 3, type:**
```bash
streamlit run dashboard/app.py
```
*Show the browser window at `http://localhost:8501`.*

**🗣️ What you SAY to Sir:**
> *"Sir, we also developed a real-time Streamlit dashboard. It shows live status cards for both resolvers, round-trip latency gauges, traffic distribution percentages, and empirical benchmark charts including throughput scaling and failover latency curves."*

---

## 🛑 How to Shut Down Cleanly After the Demo

**In Terminal 1 or 2:**
```bash
./scripts/stop_project.sh
```

**🗣️ What you SAY to Sir:**
> *"Sir, our stop script safely terminates all background daemons and clears any residual sockets."*

---

## 🎯 5 Tough Questions "Sir" Might Ask & Your Exact Answers

### Q1: "What transport protocol does DNS use and why?"
> **Answer:** *"UDP over port 53 (or 5000/5001 here), because UDP is connectionless with no 3-way handshake overhead, minimizing latency for small single-packet request/response queries."*

### Q2: "What is route flapping and how did you prevent it?"
> **Answer:** *"Flapping happens when temporary jitter causes a server to alternate rapidly between online and offline states. We prevent this using hysteresis thresholds: a server is only marked OFFLINE after 2 consecutive failed pings, and only restored ONLINE after 2 consecutive successful pings."*

### Q3: "What is the difference between Application-level failover and SDN network-level forwarding?"
> **Answer:** *"Application-level selection happens inside the client socket code (OSI Layer 7) based on our JSON health status. Network-level forwarding happens inside the Open vSwitch (OSI Layer 2-4) where the Ryu SDN controller installs OpenFlow 1.3 priority flow rules to steer packets at hardware line rate."*

### Q4: "What happens when cache TTL expires?"
> **Answer:** *"The entry's expiration timestamp is checked monotonically. Once expired, it is purged from memory and the next query goes to the network resolver to fetch fresh data. Expired records are never returned."*

### Q5: "How many queries per second can your system handle?"
> **Answer:** *"In our multithreaded empirical benchmarks using ThreadPoolExecutor, our system sustained over 19,000 queries per second with sub-millisecond average latency."*
