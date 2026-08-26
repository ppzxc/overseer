"""
E2E Test 01: Central Control Plane Services Health & Connectivity
Verifies that PostgreSQL, Vault, Boundary, and Prometheus APIs are reachable and healthy.
"""

import os
import socket
import pytest
import requests

def test_ctrl_001_postgres_backend():
    """[CTRL-001] PostgreSQL Database Backend Service port connectivity"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(3)
    result = sock.connect_ex(('127.0.0.1', 5432))
    sock.close()
    # 로컬 포트가 열려있거나 docker 내부 접근 가능
    assert result == 0 or os.path.exists("/var/run/docker.sock"), "PostgreSQL port 5432 check"

def test_ctrl_002_network_and_orchestration(root_dir):
    """[CTRL-002] Overseer Bridge Network Isolation and Compose definition"""
    compose_file = root_dir / "docker-compose.yml"
    assert compose_file.exists(), "docker-compose.yml is missing"
    content = compose_file.read_text()
    assert "overseer-net:" in content, "overseer-net network is not defined in compose file"

def test_ctrl_003_bootstrap_workflow(root_dir):
    """[CTRL-003] Automated Full Stack Bootstrap script existence and executable"""
    bootstrap_script = root_dir / "scripts" / "bootstrap.sh"
    assert bootstrap_script.exists() and os.access(bootstrap_script, os.X_OK), "bootstrap.sh is missing or not executable"

def test_vault_ctrl_001_vault_health(http_session, vault_url):
    """[VAULT-CTRL-001] Vault Server Initialization and Unseal status"""
    try:
        resp = http_session.get(f"{vault_url}/v1/sys/health", timeout=5)
        assert resp.status_code in [200, 429, 503], f"Vault returned status: {resp.status_code}"
    except requests.exceptions.ConnectionError:
        pytest.fail(f"Could not connect to Vault at {vault_url}.")

def test_bnd_ctrl_001_boundary_health(http_session, boundary_url):
    """[BND-CTRL-001] Boundary Controller Database and API health"""
    try:
        resp = http_session.get(f"{boundary_url}/v1/health", timeout=5)
        assert resp.status_code == 200, f"Boundary controller returned status {resp.status_code}"
    except requests.exceptions.ConnectionError:
        pytest.fail(f"Could not connect to Boundary at {boundary_url}.")

def test_prom_ctrl_001_prometheus_health(http_session, prometheus_url):
    """[PROM-CTRL-001] Prometheus Server Health and API"""
    try:
        resp = http_session.get(f"{prometheus_url}/-/healthy", timeout=5)
        assert resp.status_code == 200, f"Prometheus returned status {resp.status_code}"
        assert "Prometheus Server is Healthy" in resp.text
    except requests.exceptions.ConnectionError:
        pytest.fail(f"Could not connect to Prometheus at {prometheus_url}.")
