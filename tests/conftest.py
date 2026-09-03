"""
Pytest configuration and shared fixtures for Overseer E2E System Integration Testing
"""

import os
import json
import pytest
import requests
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent

@pytest.fixture(scope="session")
def root_dir():
    return ROOT_DIR

@pytest.fixture(scope="session")
def openbao_url():
    return os.getenv("BAO_ADDR", "http://127.0.0.1:8200")

@pytest.fixture(scope="session")
def boundary_url():
    return os.getenv("BOUNDARY_ADDR", "http://127.0.0.1:9200")

@pytest.fixture(scope="session")
def semaphore_url():
    return os.getenv("SEMAPHORE_ADDR", "http://127.0.0.1:3000")

@pytest.fixture(scope="session")
def openbao_token(root_dir):
    env_token = os.getenv("BAO_TOKEN")
    if env_token:
        return env_token
    data_dir_env = os.getenv("DATA_DIR", "/data")
    search_paths = [
        Path(data_dir_env) / "openbao" / "openbao-init.json",
        root_dir / "openbao" / "data" / "openbao-init.json",
        root_dir / "data" / "openbao" / "openbao-init.json",
    ]
    for p in search_paths:
        if p.exists():
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                tok = data.get("root_token", "")
                if tok:
                    return tok
            except Exception:
                pass
    return "root"

@pytest.fixture(scope="session")
def http_session():
    session = requests.Session()
    session.headers.update({"User-Agent": "Overseer-E2E-Tester"})
    return session
