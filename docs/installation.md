# Installation & Environment Setup Guide

**Target OS:** Ubuntu Linux 20.04 LTS / 22.04 LTS / 24.04 LTS  
**Python Runtime:** Python 3.10, 3.11, or 3.12  
**Network Emulator:** Mininet 2.3.0+  
**Virtual Switch:** Open vSwitch (OVS) 2.13+  
**SDN Framework:** OS-Ken / Ryu / Standalone Engine  

---

## 1. Compatibility Matrix

| Component | Tested Version | Ubuntu 20.04 | Ubuntu 22.04 | Ubuntu 24.04 | macOS (Dev/Test) |
|---|---|---|---|---|---|
| **Python** | 3.10 / 3.11 / 3.12 | Native (3.8->3.10) | Native (3.10) | Native (3.12) | Native (3.11) |
| **Open vSwitch** | 2.17.x / 3.x | Fully Supported | Fully Supported | Fully Supported | N/A (Emulated) |
| **Mininet** | 2.3.0 / 2.3.1 | Native | Native | Native | N/A (Emulated) |
| **SDN Controller**| OS-Ken 2.7+ / Ryu | Supported | Recommended (os-ken) | Recommended (os-ken) | Standalone Engine |
| **Matplotlib** | 3.8+ / 3.11+ | Supported | Supported | Supported | Supported |
| **Streamlit** | 1.30+ / 1.40+ | Supported | Supported | Supported | Supported |

> [!NOTE]
> On modern Ubuntu releases (22.04 and 24.04), `os-ken` is the recommended, actively maintained fork of Ryu with full support for Python 3.10+ and OpenFlow 1.3. On macOS or non-Linux workstations, the system automatically uses the included Standalone OpenFlow 1.3 Controller Engine.

---

## 2. Automated One-Command Installation

To install all system tools, Mininet, Open vSwitch, and Python packages automatically on Ubuntu, run:

```bash
chmod +x scripts/install.sh
./scripts/install.sh
```

---

## 3. Manual Step-by-Step Installation Instructions

If you prefer to install packages manually or need to troubleshoot specific components, follow these steps:

### Step 3.1: Update System Repositories and Install Toolchains
```bash
sudo apt-get update -y && sudo apt-get upgrade -y
sudo apt-get install -y python3 python3-pip python3-dev git curl build-essential \
                        openvswitch-switch openvswitch-testcontroller net-tools iproute2
```

### Step 3.2: Install Mininet Network Emulator
```bash
sudo apt-get install -y mininet

# Verify Mininet and Open vSwitch installation
sudo mn --version
sudo ovs-vsctl --version

# Run a baseline sanity check
sudo mn --test pingall
```

### Step 3.3: Configure Open vSwitch Service
Ensure the Open vSwitch daemon is running:
```bash
sudo systemctl enable openvswitch-switch
sudo systemctl restart openvswitch-switch
sudo systemctl status openvswitch-switch
```

### Step 3.4: Set Up Python Virtual Environment (Recommended)
```bash
# Install venv package
sudo apt-get install -y python3-venv

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate
```

### Step 3.5: Install Project Python Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 3.6: Verify Python Installations
Run the following one-liner to confirm all libraries are correctly imported:
```bash
python3 -c "import pytest, matplotlib, pandas, streamlit; print('All core Python packages imported successfully!')"
```

---

## 4. Verification and Sanity Testing

Run the automated pytest test suite to ensure the installation is 100% operational:

```bash
pytest tests/ -v
```

Expected output:
```
============================== 25 passed in ~5s ==============================
```
