#!/usr/bin/env bash
# ==============================================================================
# Service Startup Script for DNS-SDN Resolution System
# Launches: SDN Controller, Resolver A, Resolver B, and Health Monitor
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
PID_FILE="$PROJECT_ROOT/.project_pids"

# Clean up any existing instances first
"$SCRIPT_DIR/stop_project.sh" > /dev/null 2>&1 || true

echo "================================================================="
echo "       STARTING DNS-SDN RESOLUTION SYSTEM SERVICES               "
echo "================================================================="

mkdir -p "$PROJECT_ROOT/logs" "$PROJECT_ROOT/results"

# 1. Start SDN Controller on Port 6653
echo "[1/4] Starting SDN OpenFlow 1.3 Controller (port 6653)..."
python3 "$PROJECT_ROOT/sdn/sdn_controller.py" --standalone > "$PROJECT_ROOT/logs/sdn_controller.log" 2>&1 &
CONTROLLER_PID=$!
echo "      Controller PID: $CONTROLLER_PID (Log: logs/sdn_controller.log)"

# 2. Start Resolver A on Port 5000
echo "[2/4] Starting Resolver A (127.0.0.1:5000)..."
python3 "$PROJECT_ROOT/resolver/resolver.py" --name "Resolver A" --host "127.0.0.1" --port 5000 > "$PROJECT_ROOT/logs/resolver_a.log" 2>&1 &
RESOLVER_A_PID=$!
echo "      Resolver A PID: $RESOLVER_A_PID (Log: logs/resolver_a.log)"

# 3. Start Resolver B on Port 5001
echo "[3/4] Starting Resolver B (127.0.0.1:5001)..."
python3 "$PROJECT_ROOT/resolver/resolver.py" --name "Resolver B" --host "127.0.0.1" --port 5001 > "$PROJECT_ROOT/logs/resolver_b.log" 2>&1 &
RESOLVER_B_PID=$!
echo "      Resolver B PID: $RESOLVER_B_PID (Log: logs/resolver_b.log)"

sleep 1

# 4. Start Health Monitor
echo "[4/4] Starting Resolver Health Monitor..."
python3 "$PROJECT_ROOT/monitoring/health_monitor.py" --local > "$PROJECT_ROOT/logs/health_monitor.log" 2>&1 &
HEALTH_PID=$!
echo "      Health Monitor PID: $HEALTH_PID (Log: logs/health_monitor.log)"

# Record PIDs for clean shutdown
echo "$CONTROLLER_PID $RESOLVER_A_PID $RESOLVER_B_PID $HEALTH_PID" > "$PID_FILE"

sleep 1
echo "================================================================="
echo "  All background services are running successfully!             "
echo ""
echo "  To run interactive DNS Client:"
echo "    python3 client/client.py --local"
echo ""
echo "  To launch Streamlit Dashboard:"
echo "    streamlit run dashboard/app.py"
echo ""
echo "  To execute Mininet topology (on Ubuntu):"
echo "    sudo python3 mininet/mininet_topology.py --auto-start"
echo ""
echo "  To stop all services:"
echo "    ./scripts/stop_project.sh"
echo "================================================================="

