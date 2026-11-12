#!/usr/bin/env python3
"""
Root entry point for UDP Resolver Server (Backwards compatible wrapper).
Delegates to resolver.resolver.main.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from resolver.resolver import main

if __name__ == "__main__":
    main()
