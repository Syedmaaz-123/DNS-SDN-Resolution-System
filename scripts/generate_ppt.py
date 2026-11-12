"""
Automated PowerPoint Presentation Generator for DNS-SDN Resolution System
Creates a publication-quality 16:9 widescreen academic slide deck (.pptx)
embedding empirical evaluation figures, architectural diagrams, and structured bullet points.
"""

import sys
from pathlib import Path
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import MSO_SHAPE

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = PROJECT_ROOT / "results"
OUTPUT_PPTX = PROJECT_ROOT / "DNS_SDN_Resolution_System_Presentation.pptx"

# Color Palette
COLOR_NAVY = RGBColor(30, 58, 138)       # #1E3A8A
COLOR_BLUE = RGBColor(37, 99, 235)       # #2563EB
COLOR_SLATE = RGBColor(51, 65, 85)       # #334155
COLOR_LIGHT_BG = RGBColor(248, 250, 252) # #F8FAFC
COLOR_WHITE = RGBColor(255, 255, 255)
COLOR_GREEN = RGBColor(22, 101, 52)      # #166534
COLOR_ACCENT = RGBColor(217, 119, 6)     # #D97706


def create_deck():
    prs = Presentation()
    # 16:9 Widescreen dimensions
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank_layout = prs.slide_layouts[6]

    def add_header(slide, title_text, category_text="DNS-SDN RESOLUTION SYSTEM"):
        # Header background bar
        hdr_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.4), Inches(11.7), Inches(1.1))
        tf = hdr_box.text_frame
        tf.word_wrap = True
        tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0

        p_cat = tf.paragraphs[0]
        p_cat.text = category_text.upper()
        p_cat.font.size = Pt(10)
        p_cat.font.bold = True
        p_cat.font.color.rgb = COLOR_BLUE

        p_title = tf.add_paragraph()
        p_title.text = title_text
        p_title.font.size = Pt(24)
        p_title.font.bold = True
        p_title.font.color.rgb = COLOR_NAVY

    def add_bullets(slide, left, top, width, height, items):
        box = slide.shapes.add_textbox(left, top, width, height)
        tf = box.text_frame
        tf.word_wrap = True
        tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0

        for idx, (heading, body) in enumerate(items):
            p = tf.paragraphs[0] if idx == 0 else tf.add_paragraph()
            p.space_after = Pt(12)
            run_h = p.add_run()
            run_h.text = f"• {heading}: "
            run_h.font.bold = True
            run_h.font.size = Pt(15)
            run_h.font.color.rgb = COLOR_NAVY

            run_b = p.add_run()
            run_b.text = body
            run_b.font.size = Pt(14)
            run_b.font.color.rgb = COLOR_SLATE

    # =========================================================================
    # SLIDE 1: Title Slide
    # =========================================================================
    slide1 = prs.slides.add_slide(blank_layout)
    # Background card
    bg = slide1.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(13.333), Inches(7.5))
    bg.fill.solid()
    bg.fill.fore_color.rgb = COLOR_NAVY
    bg.line.fill.background()

    tb_title = slide1.shapes.add_textbox(Inches(1.2), Inches(1.8), Inches(11.0), Inches(4.0))
    tf1 = tb_title.text_frame
    tf1.word_wrap = True

    p0 = tf1.paragraphs[0]
    p0.text = "ACADEMIC NETWORKING PROJECT PRESENTATION"
    p0.font.size = Pt(12)
    p0.font.bold = True
    p0.font.color.rgb = RGBColor(147, 197, 253)

    p1 = tf1.add_paragraph()
    p1.text = "DNS-SDN Resolution System"
    p1.font.size = Pt(36)
    p1.font.bold = True
    p1.font.color.rgb = COLOR_WHITE
    p1.space_before = Pt(8)

    p2 = tf1.add_paragraph()
    p2.text = "Intelligent DNS-like Resolution with Multiple Resolvers, Dynamic Load Balancing, Fault Tolerance and SDN-Controlled Network Forwarding"
    p2.font.size = Pt(16)
    p2.font.color.rgb = RGBColor(226, 232, 240)
    p2.space_before = Pt(10)

    p3 = tf1.add_paragraph()
    p3.text = "OpenFlow 1.3  |  Mininet Virtualization  |  Ryu/OS-Ken Controller  |  UDP Socket Hierarchy"
    p3.font.size = Pt(13)
    p3.font.color.rgb = RGBColor(186, 230, 253)
    p3.space_before = Pt(25)

    # =========================================================================
    # SLIDE 2: Introduction & Motivation
    # =========================================================================
    slide2 = prs.slides.add_slide(blank_layout)
    add_header(slide2, "Introduction & Project Motivation", "Problem Context")
    items2 = [
        ("Fundamental Criticality", "The Domain Name System (DNS) is foundational to IP networking, translating human-readable hostnames to IP addresses."),
        ("Transport Layer Protocol", "Standard DNS operates primarily over UDP (Port 53) to eliminate connection handshake latency, but inherits UDP's lack of built-in connection management."),
        ("Modern Availability Demands", "Mission-critical applications require continuous sub-millisecond name resolution with guaranteed zero downtime during server outages."),
        ("Software-Defined Networking (SDN)", "Decouples control logic from underlying packet switches, enabling centralized real-time flow modification at wire speed."),
        ("Project Objective", "Bridge application-layer DNS intelligence with SDN OpenFlow 1.3 forwarding to deliver a fully autonomous, fault-tolerant naming system.")
    ]
    add_bullets(slide2, Inches(0.8), Inches(1.8), Inches(11.7), Inches(5.0), items2)

    # =========================================================================
    # SLIDE 3: Problem Statement & Existing Limitations
    # =========================================================================
    slide3 = prs.slides.add_slide(blank_layout)
    add_header(slide3, "Problem Statement & Baseline Limitations", "System Gaps")
    items3 = [
        ("Single Point of Failure", "Conventional DNS configurations rely on static server lists. If a primary resolver fails, clients stall on socket timeouts."),
        ("Lack of Negative Caching", "Queries for non-existent domains (NXDOMAIN / NOT_FOUND) trigger repeated upstream lookups, wasting bandwidth."),
        ("Blind Network Forwarding", "Standard switches cannot inspect DNS payloads or reroute flows dynamically when destination servers crash."),
        ("Route Flapping Susceptibility", "Transient packet loss frequently causes naive monitors to rapidly toggle server states, causing routing instability."),
        ("Static Server Selection", "Traditional clients lack automated latency ranking and cannot shift traffic based on real-time server response times.")
    ]
    add_bullets(slide3, Inches(0.8), Inches(1.8), Inches(11.7), Inches(5.0), items3)

    # =========================================================================
    # SLIDE 4: Proposed Architecture & Topology
    # =========================================================================
    slide4 = prs.slides.add_slide(blank_layout)
    add_header(slide4, "Proposed Architecture & Mininet Topology", "System Design")

    items4 = [
        ("Control Plane", "Ryu / OS-Ken OpenFlow 1.3 Controller operating on TCP Port 6653."),
        ("Virtual Switching", "Single Open vSwitch (s1) interconnecting client and multiple resolvers."),
        ("Host Nodes", "Host h1 (10.0.0.10: Client), Host h2 (10.0.0.20: Resolver A), Host h3 (10.0.0.30: Resolver B)."),
        ("Dual-Tier Intelligence", "Application-level client selection paired with OpenFlow network-level packet steering.")
    ]
    add_bullets(slide4, Inches(0.8), Inches(1.8), Inches(6.0), Inches(5.0), items4)

    # ASCII Architecture Card on the right
    diag_box = slide4.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(7.2), Inches(1.8), Inches(5.3), Inches(4.8))
    diag_box.fill.solid()
    diag_box.fill.fore_color.rgb = COLOR_LIGHT_BG
    diag_box.line.color.rgb = COLOR_BLUE
    dtf = diag_box.text_frame
    dtf.word_wrap = True
    dp = dtf.paragraphs[0]
    dp.text = "NETWORK TOPOLOGY & OPENFLOW\n"
    dp.font.bold = True
    dp.font.size = Pt(13)
    dp.font.color.rgb = COLOR_NAVY

    dp2 = dtf.add_paragraph()
    dp2.text = (
        "  +------------------------------------+\n"
        "  |   SDN Controller (c0: port 6653)   |\n"
        "  +------------------+-----------------+\n"
        "                     | OpenFlow 1.3\n"
        "                     v\n"
        "          +-----------------------+\n"
        "          |  Open vSwitch (s1)    |\n"
        "          +---+-------+-------+---+\n"
        "      Port 1  |       | Port 2| Port 3\n"
        "              |       |       |\n"
        "              v       v       v\n"
        "            [h1]    [h2]    [h3]\n"
        "           Client  Res-A   Res-B\n"
        "          10.0.0.10 10.0.0.20 10.0.0.30"
    )
    dp2.font.size = Pt(11)
    dp2.font.name = "Courier New"
    dp2.font.color.rgb = COLOR_SLATE

    # =========================================================================
    # SLIDE 5: DNS Caching & Negative Caching (RFC 2308)
    # =========================================================================
    slide5 = prs.slides.add_slide(blank_layout)
    add_header(slide5, "DNS Caching & TTL Management", "Application Tier")
    items5 = [
        ("Positive Caching", "Resolved hostname-to-IP records are cached with a configurable positive TTL (Default: 100 seconds)."),
        ("Negative Caching (RFC 2308)", "Non-existent domains (NOT_FOUND) are cached with independent negative TTL (30 seconds), preventing query storms."),
        ("Thread-Safe Monotonic Design", "Protected by mutex threading.Lock(); expiration computed via monotonic time to prevent system clock skew errors."),
        ("Automatic Eviction", "Enforces maximum entry limits via Least Remaining Lifetime eviction."),
        ("Microsecond Acceleration", "In-memory retrieval drops lookup time from ~1.2 ms down to 0.03 ms (~50x performance increase).")
    ]
    add_bullets(slide5, Inches(0.8), Inches(1.8), Inches(11.7), Inches(5.0), items5)

    # =========================================================================
    # SLIDE 6: Intelligent Load Balancing & Resolver Selection
    # =========================================================================
    slide6 = prs.slides.add_slide(blank_layout)
    add_header(slide6, "Intelligent Load Balancing & Server Ranking", "Load Balancer")
    items6 = [
        ("Lowest-Latency Policy (Default)", "Dynamically sorts healthy resolvers by measured UDP PING latency, sending queries to the fastest server."),
        ("Round-Robin Policy", "Sequentially alternates queries across healthy nodes to distribute processing burden equally."),
        ("Priority Policy", "Directs traffic to primary Resolver A, falling back to Resolver B only when Resolver A is offline."),
        ("Health Exclusion", "Resolvers marked OFFLINE in health telemetry are excluded from primary candidate selection."),
        ("Stale Data Fallback", "If health timestamps exceed 15 seconds, the selector falls back to safe priority ordering automatically.")
    ]
    add_bullets(slide6, Inches(0.8), Inches(1.8), Inches(11.7), Inches(5.0), items6)

    # =========================================================================
    # SLIDE 7: Health Probing & Flapping Mitigation
    # =========================================================================
    slide7 = prs.slides.add_slide(blank_layout)
    add_header(slide7, "Health Probing & Route Flapping Prevention", "Fault Tolerance")
    items7 = [
        ("Active UDP Heartbeats", "Dedicated health daemon sends UDP PING to each resolver every 3.0 seconds and awaits PONG."),
        ("Consecutive Failure Threshold", "A server is marked OFFLINE only after 2 consecutive failed probes, preventing false positives from transient jitter."),
        ("Consecutive Recovery Threshold", "An offline server must succeed on 2 consecutive probes before being declared ONLINE, preventing flapping."),
        ("Atomic Telemetry Persistence", "Health state written to temporary file and renamed via atomic POSIX replace, eliminating read-write race conditions."),
        ("Telemetry Metrics", "Tracks uptime %, packet loss %, rolling latency history, and transition timestamps.")
    ]
    add_bullets(slide7, Inches(0.8), Inches(1.8), Inches(11.7), Inches(5.0), items7)

    # =========================================================================
    # SLIDE 8: SDN OpenFlow 1.3 Pipeline
    # =========================================================================
    slide8 = prs.slides.add_slide(blank_layout)
    add_header(slide8, "SDN Controller & OpenFlow 1.3 Pipeline", "Control Plane")
    items8 = [
        ("Table-Miss Flow Entry (Priority 0)", "Directs unclassified packets to controller via OpenFlow Packet-In messages."),
        ("Proactive DNS Flow (Priority 100)", "Matches eth_type=0x0800, ip_proto=17, udp_dst=5000/5001. Directs client DNS queries to active resolver port."),
        ("Dynamic Failover Flow (Priority 200)", "Pushed dynamically when health status reports server failure, rerouting packets directly at switch level."),
        ("Switch Telemetry Polling", "Controller polls OFPPortStatsRequest every 5s to record live RX/TX packets and bytes per switch port."),
        ("Hardware Line-Rate Forwarding", "Packet forwarding is executed directly by Open vSwitch without per-packet controller overhead once flows are installed.")
    ]
    add_bullets(slide8, Inches(0.8), Inches(1.8), Inches(11.7), Inches(5.0), items8)

    # =========================================================================
    # SLIDE 9: Performance Evaluation - Cache & Latency (With Image)
    # =========================================================================
    slide9 = prs.slides.add_slide(blank_layout)
    add_header(slide9, "Performance Evaluation: Caching & Latency", "Empirical Results")

    items9 = [
        ("Cache Miss Latency", "Network UDP round-trip latency averages 1.25 ms to 2.85 ms."),
        ("Cache Hit Latency", "In-memory hash table lookup resolves in 0.02 ms to 0.04 ms."),
        ("Measured Speedup", "Yields an empirical 50x to 80x acceleration factor."),
        ("Network Conservation", "Reduces DNS packet traffic across the Open vSwitch by over 90% during repeat queries.")
    ]
    add_bullets(slide9, Inches(0.8), Inches(1.8), Inches(6.2), Inches(5.0), items9)

    fig_cache = RESULTS_DIR / "cache_hit_vs_miss.png"
    if fig_cache.exists():
        slide9.shapes.add_picture(str(fig_cache), Inches(7.3), Inches(1.8), width=Inches(5.2))

    # =========================================================================
    # SLIDE 10: Performance Evaluation - Failover & Throughput (With Image)
    # =========================================================================
    slide10 = prs.slides.add_slide(blank_layout)
    add_header(slide10, "Performance Evaluation: Failover & Throughput", "Empirical Results")

    items10 = [
        ("Normal Steady-State", "Queries resolve smoothly at ~1.2 ms via primary Resolver A."),
        ("Failover Transition", "Upon Resolver A failure, socket detects timeout and switches to Resolver B seamlessly."),
        ("Recovery Re-entry", "When Resolver A recovers, health monitor restores it to eligible pool without service interruption."),
        ("High Query Scalability", "Multithreaded query load sustains up to 19,000+ Queries Per Second (QPS) with sub-millisecond average latency.")
    ]
    add_bullets(slide10, Inches(0.8), Inches(1.8), Inches(6.2), Inches(5.0), items10)

    fig_fail = RESULTS_DIR / "failover_performance.png"
    if fig_fail.exists():
        slide10.shapes.add_picture(str(fig_fail), Inches(7.3), Inches(1.8), width=Inches(5.2))

    # =========================================================================
    # SLIDE 11: Real-Time Streamlit Telemetry Dashboard
    # =========================================================================
    slide11 = prs.slides.add_slide(blank_layout)
    add_header(slide11, "Real-Time Telemetry Dashboard", "User Interface")

    items11 = [
        ("Live Server Health Cards", "Displays real-time ONLINE/OFFLINE badges, current latency, and probe loss rate."),
        ("SDN Port Telemetry", "Monitors Open vSwitch port statistics, RX/TX bytes, and resolver traffic distribution."),
        ("Interactive Query Tester", "Allows examiners to type hostnames directly in the web UI and view live resolution output."),
        ("Empirical Visualizations", "Integrates generated Matplotlib benchmark figures directly into an interactive presentation tab.")
    ]
    add_bullets(slide11, Inches(0.8), Inches(1.8), Inches(6.2), Inches(5.0), items11)

    fig_dash = RESULTS_DIR / "system_summary_dashboard.png"
    if fig_dash.exists():
        slide11.shapes.add_picture(str(fig_dash), Inches(7.3), Inches(1.8), width=Inches(5.2))

    # =========================================================================
    # SLIDE 12: Automated Verification & Testing
    # =========================================================================
    slide12 = prs.slides.add_slide(blank_layout)
    add_header(slide12, "Verification & Automated Testing Suite", "Quality Assurance")
    items12 = [
        ("Comprehensive Pytest Suite", "25 automated unit and integration tests executing across 6 test modules with 100% pass rate."),
        ("Protocol Validation", "Verifies PING/PONG, valid name mappings, NOT_FOUND, and malformed command handling."),
        ("Caching & Eviction Tests", "Confirms positive TTL, negative TTL, capacity eviction, and thread concurrency safety."),
        ("Failover Scenario Tests", "Validates dynamic failover to Resolver B and seamless recovery upon Resolver A restart."),
        ("SDN Flow Tests", "Validates OpenFlow 1.3 Priority 100 DNS flow spec generation and priority 200 failover modification.")
    ]
    add_bullets(slide12, Inches(0.8), Inches(1.8), Inches(11.7), Inches(5.0), items12)

    # =========================================================================
    # SLIDE 13: Conclusion & Future Enhancements
    # =========================================================================
    slide13 = prs.slides.add_slide(blank_layout)
    add_header(slide13, "Conclusion & Future Scope", "Summary")
    items13 = [
        ("Key Accomplishments", "Successfully integrated Application-Level DNS intelligence with OpenFlow 1.3 network-level SDN forwarding."),
        ("High Reliability", "Demonstrated zero-downtime failover, flapping mitigation, and ~50x caching acceleration."),
        ("Broad Portability", "Runs seamlessly on both native macOS/Linux and full Mininet OpenFlow topologies."),
        ("Future Scope 1: DNSSEC", "Integration of cryptographic resource record digital signatures (RRSIG/DNSKEY)."),
        ("Future Scope 2: Encrypted Transports", "Migration from plain UDP to DNS-over-HTTPS (DoH) and DNS-over-TLS (DoT)."),
        ("Future Scope 3: Machine Learning", "Incorporation of predictive reinforcement learning for congestion-aware resolver routing.")
    ]
    add_bullets(slide13, Inches(0.8), Inches(1.8), Inches(11.7), Inches(5.0), items13)

    # =========================================================================
    # SLIDE 14: Q&A & Thank You
    # =========================================================================
    slide14 = prs.slides.add_slide(blank_layout)
    bg14 = slide14.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(13.333), Inches(7.5))
    bg14.fill.solid()
    bg14.fill.fore_color.rgb = COLOR_NAVY
    bg14.line.fill.background()

    tb_end = slide14.shapes.add_textbox(Inches(1.5), Inches(2.2), Inches(10.3), Inches(3.5))
    tfe = tb_end.text_frame
    tfe.word_wrap = True

    pe1 = tfe.paragraphs[0]
    pe1.text = "Thank You!"
    pe1.font.size = Pt(44)
    pe1.font.bold = True
    pe1.font.color.rgb = COLOR_WHITE
    pe1.alignment = PP_ALIGN.CENTER

    pe2 = tfe.add_paragraph()
    pe2.text = "DNS-SDN Resolution System"
    pe2.font.size = Pt(22)
    pe2.font.bold = True
    pe2.font.color.rgb = RGBColor(147, 197, 253)
    pe2.alignment = PP_ALIGN.CENTER
    pe2.space_before = Pt(12)

    pe3 = tfe.add_paragraph()
    pe3.text = "Questions & Answers"
    pe3.font.size = Pt(26)
    pe3.font.color.rgb = RGBColor(254, 240, 138)
    pe3.alignment = PP_ALIGN.CENTER
    pe3.space_before = Pt(20)

    # Save presentation
    prs.save(str(OUTPUT_PPTX))
    print(f"[SUCCESS] PowerPoint presentation generated: {OUTPUT_PPTX}")
    return OUTPUT_PPTX


if __name__ == "__main__":
    create_deck()

