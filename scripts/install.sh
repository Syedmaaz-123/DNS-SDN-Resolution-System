#!/usr/bin/env bash
# ==============================================================================
# Installation Script for DNS-SDN Resolution System
# Target Environment: Ubuntu Linux (20.04 LTS / 22.04 LTS / 24.04 LTS)
# ==============================================================================

set -e

echo "================================================================="
echo "  Installing DNS-SDN Resolution System Dependencies on Ubuntu    "
echo "================================================================="

# 1. System Package Updates & Essential Tools
echo "[STEP 1/5] Updating APT package repositories..."
sudo apt-get update -y
sudo apt-get install -y python3 python3-pip python3-dev git curl build-essential \
                        openvswitch-switch openvswitch-testcontroller net-tools iproute2

# 2. Mininet Installation
echo "[STEP 2/5] Installing Mininet network emulator..."
if command -v mn &> /dev/null; then
    echo "  Mininet already installed: $(mn --version 2>&1)"
else
    sudo apt-get install -y mininet
    echo "  Mininet installed successfully."
fi

# Ensure Open vSwitch service is active
echo "  Starting Open vSwitch service..."
sudo systemctl enable openvswitch-switch || true
sudo systemctl restart openvswitch-switch || true

# 3. Python Core Dependencies
echo "[STEP 3/5] Installing Python libraries from requirements.txt..."
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

python3 -m pip install --upgrade pip
python3 -m pip install -r "$PROJECT_ROOT/requirements.txt"

# 4. SDN Controller Framework (Ryu or OS-Ken)
echo "[STEP 4/5] Checking SDN Controller installation (OS-Ken / Ryu)..."
# In modern Python 3.10+ environments, os-ken is the maintained fork of Ryu
if python3 -c "import ryu" 2>/dev/null; then
    echo "  Ryu framework detected."
elif python3 -c "import os_ken" 2>/dev/null; then
    echo "  OS-Ken framework detected."
else
    echo "  Installing os-ken (modern Ryu-compatible OpenFlow 1.3 framework)..."
    python3 -m pip install os-ken || python3 -m pip install ryu || echo "Note: Using Standalone OpenFlow 1.3 Controller engine."
fi

# 5. Directory structure & Permissions
echo "[STEP 5/5] Ensuring project directories and permissions..."
mkdir -p "$PROJECT_ROOT/logs" "$PROJECT_ROOT/results"
chmod +x "$PROJECT_ROOT/scripts/"*.sh || true

echo "================================================================="
echo "  Installation Complete!                                         "
echo "  Run './scripts/start_project.sh' to launch services.           "
echo "================================================================="
