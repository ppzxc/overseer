"""
E2E Test 04: Semaphore UI & GitOps Orchestration Architecture Test
Verifies that Overseer Control Plane correctly configures Semaphore UI as the unified
GitOps orchestrator, managing task templates, remote Git repository links, OpenBao CA mounts,
and inventory blueprints without tightly coupling to internal Ansible role implementations.
"""

import os
import yaml
import pytest
from pathlib import Path

def test_ctrl_004_semaphore_service_definition(root_dir):
    """[CTRL-004] Semaphore UI container definition and PostgreSQL backend integration"""
    compose_file = root_dir / "compose.yml"
    assert compose_file.exists(), "compose.yml is missing"
    compose_content = compose_file.read_text(encoding="utf-8")
    
    # 1. Semaphore 서비스 및 포트 정의 검증
    assert "semaphore:" in compose_content, "semaphore service must be defined in compose.yml"
    assert "image: semaphoreui/semaphore:" in compose_content, "Semaphore image must be configured"
    assert "3000:3000" in compose_content, "Semaphore port 3000 must be exposed"
    assert "SEMAPHORE_DB_DIALECT: postgres" in compose_content, "Postgres dialect must be configured"
    
    # 2. 전용 데이터 볼륨 및 OpenBao CA 마운트 검증
    assert "${DATA_DIR:-/data}/semaphore:/tmp/semaphore" in compose_content, "Semaphore must use dedicated data volume"
    assert "${DATA_DIR:-/data}/openbao:/openbao/data:ro" in compose_content, "Semaphore must mount OpenBao data volume"

def test_ctrl_005_gitops_seeding_contract(root_dir):
    """[CTRL-005] Semaphore GitOps Project, Repository, and Task Templates Seeding Blueprint"""
    init_script = root_dir / "scripts" / "init-semaphore.sh"
    assert init_script.exists() and os.access(init_script, os.X_OK), "scripts/init-semaphore.sh is missing or not executable"
    script_content = init_script.read_text(encoding="utf-8")
    
    # 1. 원격 GitOps 레포지토리 연동 검증
    assert "ANSIBLE_REPO_URL" in script_content, "GitOps repository URL variable must be defined"
    assert "Node Provisioner GitOps" in script_content, "GitOps repository name must be configured"
    
    # 2. 핵심 오케스트레이션 템플릿 계약 검증
    expected_templates = [
        "1. Provision Target Servers",
        "2. Provision Overseer Control Plane",
        "3. Provision Full Stack (All)",
        "4. Regular Maintenance & Patching",
        "5. Dry-Run Check & Diff (Simulation)",
    ]
    for tpl in expected_templates:
        assert tpl in script_content, f"Template '{tpl}' must be seeded by init-semaphore.sh"
    
    # 3. Dry-run 시뮬레이션 인자 검증
    assert "--check --diff" in script_content, "Dry-run template must pass --check --diff"

def test_semaphore_makefile_integration(root_dir):
    """Semaphore start / stop / init lifecycle targets in Makefile"""
    makefile = root_dir / "Makefile"
    assert makefile.exists(), "Makefile is missing"
    content = makefile.read_text(encoding="utf-8")
    
    assert "start-semaphore:" in content, "start-semaphore target missing in Makefile"
    assert "init-semaphore:" in content, "init-semaphore target missing in Makefile"
    assert "ensure-semaphore-db:" in content, "ensure-semaphore-db target missing in Makefile"




