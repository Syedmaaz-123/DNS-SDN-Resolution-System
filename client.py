#!/usr/bin/env python3
"""
Root entry point for DNS Client (Backwards compatible wrapper).
Delegates to client.client.DNSResolutionClient.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from client.client import main

if __name__ == "__main__":
    main()
