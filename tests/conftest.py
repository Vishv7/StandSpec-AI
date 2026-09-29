"""
Global pytest configuration and safety fixtures for StandSpec AI.
Enforces 100% offline and deterministic test execution.
"""

import socket
import pytest
import requests


@pytest.fixture(autouse=True)
def block_network_access(monkeypatch):
    """
    Autouse fixture that blockades all outbound socket/HTTP network access during tests.
    Any attempt to connect to external servers will raise RuntimeError immediately.
    """
    _orig_connect = socket.socket.connect

    def _blocked_connect(self, address, *args, **kwargs):
        # Allow loopback/local socketpair connections required by Windows asyncio proactor
        if isinstance(address, tuple) and address[0] in ("127.0.0.1", "localhost", "::1"):
            return _orig_connect(self, address, *args, **kwargs)
        raise RuntimeError(
            f"NETWORK ACCESS DETECTED: StandSpec AI test suite must run 100% offline. Attempted connect to {address}. "
            "All test data must use local fixtures or cached HTML."
        )

    # Block socket connections
    monkeypatch.setattr(socket.socket, "connect", _blocked_connect)

    # Block requests.Session.send directly as a second defense layer
    def _blocked_send(*args, **kwargs):
        raise RuntimeError(
            "HTTP REQUEST DETECTED: StandSpec AI test suite must run 100% offline. "
            "External requests to standardsbis.bsbedge.com or other hosts are strictly forbidden."
        )

    monkeypatch.setattr(requests.Session, "send", _blocked_send)
