#!/usr/bin/env bash
# ==============================================================================
# Service Shutdown Script for DNS-SDN Resolution System
# Safely terminates all components and cleans up Mininet state
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
PID_FILE="$PROJECT_ROOT/.project_pids"

echo "================================================================="
echo "       STOPPING DNS-SDN RESOLUTION SYSTEM SERVICES               "
echo "================================================================="

if [ -f "$PID_FILE" ]; then
    PIDS=$(cat "$PID_FILE")
    echo "Terminating recorded process IDs: $PIDS"
    for PID in $PIDS; do
        if kill -0 "$PID" 2>/dev/null; then
            kill "$PID" 2>/dev/null || true
        fi
    done
    rm -f "$PID_FILE"
fi

# Fallback pattern kill for safety
pkill -f "resolver.py" 2>/dev/null || true
pkill -f "health_monitor.py" 2>/dev/null || true
pkill -f "sdn_controller.py" 2>/dev/null || true

# If Mininet is installed, run cleanup
if command -v mn &> /dev/null; then
    echo "Running Mininet cleanup (sudo mn -c)..."
    sudo mn -c 2>/dev/null || true
fi

echo "All DNS-SDN background processes have been terminated."
echo "================================================================="
