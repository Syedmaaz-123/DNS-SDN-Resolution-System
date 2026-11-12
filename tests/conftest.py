"""
Pytest configuration and shared fixtures for DNS-SDN Resolution System.
"""

import sys
import time
import socket
from pathlib import Path
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture
def get_free_port():
    """Returns an unused ephemeral UDP/TCP port."""
    def _alloc():
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.bind(("", 0))
        port = s.getsockname()[1]
        s.close()
        return port
    return _alloc


@pytest.fixture(autouse=True)
def clean_environment(tmp_path, monkeypatch):
    """Ensure tests run without polluting production JSON files."""
    yield
