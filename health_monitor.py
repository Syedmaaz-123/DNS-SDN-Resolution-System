#!/usr/bin/env python3
"""
Root entry point for Health Monitor (Backwards compatible wrapper).
Delegates to monitoring.health_monitor.main.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from monitoring.health_monitor import main

if __name__ == "__main__":
    main()
