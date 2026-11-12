"""
Streamlit Web Dashboard for DNS-SDN Resolution System
Visualizes real-time resolver health, active SDN forwarding state,
cache telemetry, traffic distribution, and empirical benchmark figures.
"""

import sys
import json
import time
from pathlib import Path
import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from client.client import DNSResolutionClient

# Page configuration
st.set_page_config(
    page_title="DNS-SDN Intelligent Resolution Dashboard",
    page_icon="🌐",
    layout="wide",
    initial_sidebar_state="expanded"
)

CONFIG_PATH = PROJECT_ROOT / "config" / "config.json"
HEALTH_FILE = PROJECT_ROOT / "monitoring" / "health_status.json"
SDN_STATS_FILE = PROJECT_ROOT / "sdn" / "sdn_stats.json"
RESULTS_DIR = PROJECT_ROOT / "results"


def load_json(path: Path) -> dict:
    if path.exists():
        try:
            with open(path, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


# Title Header
st.title("🌐 DNS-SDN Resolution System Dashboard")
st.caption(
    "Intelligent DNS-like Resolution with Multiple Resolvers, Dynamic Load Balancing, "
    "Fault Tolerance and SDN-Controlled Network Forwarding"
)
st.markdown("---")

# Load real-time state files
config_data = load_json(CONFIG_PATH)
health_data = load_json(HEALTH_FILE)
sdn_data = load_json(SDN_STATS_FILE)

# Sidebar: Controls & Query Simulator
with st.sidebar:
    st.header("⚙️ System Control & Query Tool")
    policy_choice = st.selectbox(
        "Load-Balancing Policy",
        ["lowest_latency", "round_robin", "priority", "random"],
        index=0
    )
    use_local = st.checkbox("Use Localhost (127.0.0.1)", value=True, help="Toggle loopback socket resolution vs Mininet IP")

    st.subheader("🔎 Live Query Tester")
    query_host = st.text_input("Enter hostname to resolve:", value="server1.local")
    if st.button("Resolve Hostname", type="primary"):
        client = DNSResolutionClient(use_local_ip=use_local, policy=policy_choice)
        res = client.resolve(query_host)
        if res["status"] == "RESOLVED":
            st.success(f"**Resolved IP:** `{res['ip']}` via **{res['source']}** ({res['total_time_ms']} ms)")
        elif res["status"] == "NOT_FOUND":
            st.warning(f"**Status:** NOT_FOUND ({res['total_time_ms']} ms)")
        else:
            st.error(f"**Status:** FAILED - All resolvers unavailable")

        st.json({
            "hostname": res["hostname"],
            "status": res["status"],
            "source": res["source"],
            "is_cached": res["is_cached"],
            "total_time_ms": res["total_time_ms"]
        })

    st.markdown("---")
    st.info("💡 Changes to health status or SDN flow updates refresh automatically on data reload.")

# SECTION 1: Top Metrics Cards
col1, col2, col3, col4 = st.columns(4)

servers = health_data.get("servers", {})
srv_a = servers.get("Resolver A", {})
srv_b = servers.get("Resolver B", {})

with col1:
    online_a = srv_a.get("online", False)
    lat_a = srv_a.get("latency_ms")
    st.metric(
        label="Resolver A Status",
        value="ONLINE" if online_a else "OFFLINE",
        delta=f"{lat_a} ms" if lat_a else "Unreachable",
        delta_color="normal" if online_a else "inverse"
    )

with col2:
    online_b = srv_b.get("online", False)
    lat_b = srv_b.get("latency_ms")
    st.metric(
        label="Resolver B Status",
        value="ONLINE" if online_b else "OFFLINE",
        delta=f"{lat_b} ms" if lat_b else "Unreachable",
        delta_color="normal" if online_b else "inverse"
    )

with col3:
    active_sdn_res = sdn_data.get("active_resolver", "Resolver A")
    active_port = sdn_data.get("active_resolver_port", 2)
    st.metric(
        label="SDN Preferred Resolver",
        value=active_sdn_res,
        delta=f"Switch Port {active_port}"
    )

with col4:
    stale_sec = time.time() - health_data.get("updated_at", time.time())
    st.metric(
        label="Health Heartbeat",
        value="ACTIVE" if stale_sec < 15 else "STALE",
        delta=f"{stale_sec:.1f}s ago"
    )

# SECTION 2: Resolver Health & SDN OpenFlow Telemetry
st.markdown("### 📊 Resolver Telemetry & SDN Traffic Forwarding")
tab1, tab2, tab3 = st.tabs(["🏥 Resolver Health Status", "🔀 SDN OpenFlow Forwarding", "📈 Empirical Benchmarks"])

with tab1:
    if servers:
        health_rows = []
        for name, info in servers.items():
            health_rows.append({
                "Resolver": name,
                "Address": f"{info.get('ip')}:{info.get('port')}",
                "Status": "ONLINE" if info.get("online") else "OFFLINE",
                "Current Latency (ms)": info.get("latency_ms"),
                "Packet Loss (%)": info.get("packet_loss_percent"),
                "Total Probes": info.get("total_probes"),
                "Successful Probes": info.get("successful_probes")
            })
        st.dataframe(pd.DataFrame(health_rows), use_container_width=True)
    else:
        st.warning("No live health data found. Please run: `python3 monitoring/health_monitor.py`")

with tab2:
    st.markdown("#### Open vSwitch (s1) Port Statistics & Forwarding Telemetry")
    port_stats = sdn_data.get("port_statistics", {})
    if port_stats:
        port_rows = []
        for p_no, p_data in port_stats.items():
            port_rows.append({
                "Switch Port": f"Port {p_no}",
                "Attached Node": p_data.get("name"),
                "RX Packets": p_data.get("rx_packets"),
                "TX Packets": p_data.get("tx_packets"),
                "RX Bytes": p_data.get("rx_bytes"),
                "TX Bytes": p_data.get("tx_bytes")
            })
        st.dataframe(pd.DataFrame(port_rows), use_container_width=True)

        dist = sdn_data.get("traffic_distribution_percent", {})
        if dist:
            st.markdown("##### Dynamic DNS Traffic Distribution")
            st.progress(dist.get("Resolver A", 50.0) / 100.0, text=f"Resolver A: {dist.get('Resolver A')}% | Resolver B: {dist.get('Resolver B')}%")
    else:
        st.info("Run `python3 sdn/sdn_controller.py` to stream live OpenFlow port telemetry.")

with tab3:
    st.markdown("#### Empirical Benchmark Results & Evaluation Figures")
    fig_summary = RESULTS_DIR / "system_summary_dashboard.png"
    fig_latency = RESULTS_DIR / "resolver_latency_comparison.png"
    fig_cache = RESULTS_DIR / "cache_hit_vs_miss.png"
    fig_failover = RESULTS_DIR / "failover_performance.png"
    fig_tput = RESULTS_DIR / "throughput_analysis.png"

    if fig_summary.exists():
        st.image(str(fig_summary), caption="Complete System Performance Dashboard", use_container_width=True)

        c_a, c_b = st.columns(2)
        with c_a:
            if fig_cache.exists():
                st.image(str(fig_cache), caption="Cache Speedup (Positive & Negative)")
            if fig_failover.exists():
                st.image(str(fig_failover), caption="Failover Latency Spike and Recovery")
        with c_b:
            if fig_latency.exists():
                st.image(str(fig_latency), caption="Resolver Latency Distribution")
            if fig_tput.exists():
                st.image(str(fig_tput), caption="Throughput Scalability Under Multi-Threading")
    else:
        st.info("Benchmark figures not yet generated. Run `python3 monitoring/performance_monitor.py` to generate.")

st.markdown("---")
st.caption("DNS-SDN Resolution System v2.0 | Developed for Academic Networking Curriculum")
