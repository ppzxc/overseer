"""
E2E Test 03: HashiCorp Boundary Zero-Trust Access Controller & Worker
Verifies that Boundary Controller and Worker processes are functional and listening.
"""

import socket
import pytest
import requests

def test_bnd_ctrl_002_cluster_port():
    """[BND-CTRL-002] Boundary Cluster Communications port 9201 connectivity"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(3)
    result = sock.connect_ex(('127.0.0.1', 9201))
    sock.close()
    assert result == 0, "Boundary Controller cluster port 9201 is not listening."

def test_bnd_ctrl_003_worker_proxy_port():
    """[BND-CTRL-003] Boundary Worker Proxy Gateway port 9202 connectivity"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(3)
    result = sock.connect_ex(('127.0.0.1', 9202))
    sock.close()
    assert result == 0, "Boundary Worker proxy port 9202 is not listening."
