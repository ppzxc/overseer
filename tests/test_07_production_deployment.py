"""
E2E Test 07: Production Deployment & Backup-Ready Sync Pipeline
Verifies that Overseer packages and syncs production-critical operational files
to the target directory (default: /opt/services/overseer), excluding dev, tests, general docs, and git files.
"""

import os
import shutil
import pytest
from pathlib import Path

def test_ctrl_008_production_deployment_module_exists(root_dir):
    """[CTRL-008] Production deployment function and CLI arguments exist in orchestrator.py"""
    orchestrator = root_dir / "scripts" / "orchestrator.py"
    assert orchestrator.exists(), "scripts/orchestrator.py is missing"
    content = orchestrator.read_text(encoding="utf-8")
    assert "deploy_to_target" in content or "install_production" in content, "deploy_to_target function missing in orchestrator.py"
    assert "--target-dir" in content, "--target-dir argument missing in orchestrator.py"
    assert "/opt/services/overseer" in content, "Default target path /opt/services/overseer missing"

def test_ctrl_008_production_sync_file_matrix(root_dir, tmp_path):
    """[CTRL-008] Verify that deploy_to_target copies only production essentials and excludes dev/test files"""
    import sys
    sys.path.insert(0, str(root_dir / "scripts"))
    import orchestrator
    
    target_dir = tmp_path / "overseer_prod"
    target_dir.mkdir(parents=True)
    (target_dir / ".env").write_text("SEMAPHORE_ACCESS_KEY_ENCRYPTION=live-secret\nEXPOSE_PORTS=true\n", encoding="utf-8")
    (target_dir / "compose.yml").write_text("obsolete combined configuration\n", encoding="utf-8")
    (target_dir / "compose.override.yml").write_text("obsolete override\n", encoding="utf-8")
    stale_boundary_dir = target_dir / "boundary"
    stale_boundary_dir.mkdir(parents=True)
    (stale_boundary_dir / "local-data.txt").write_text("preserve existing target data", encoding="utf-8")
    
    # Run deployment sync to temporary target
    copied_files = orchestrator.deploy_to_target(source_dir=root_dir, target_dir=target_dir)
    
    # 1. Essential files MUST exist in target
    assert (target_dir / "openbao" / "compose.yml").exists(), "OpenBao Compose file must be in production target"
    assert (target_dir / "semaphore" / "compose.yml").exists(), "Semaphore Compose file must be in production target"
    assert (target_dir / "semaphore" / "compose.override.yml").exists(), "Semaphore host port override must be deployed"
    assert not (target_dir / "openbao" / "compose.override.yml").exists(), "OpenBao must remain internal"
    assert not (target_dir / "compose.yml").exists(), "combined root Compose file must not be deployed"
    assert not (target_dir / "compose.override.yml").exists(), "obsolete root Compose override must be removed"
    assert (target_dir / "Makefile").exists(), "Makefile must be in production target"
    assert (target_dir / "README.md").exists(), "README.md must be in production target"
    assert (target_dir / "CONTEXT.md").exists(), "CONTEXT.md must be in production target"
    assert (target_dir / ".env.example").exists(), ".env.example must be in production target"
    assert (target_dir / "openbao" / "config").exists()
    assert (target_dir / "openbao" / "scripts" / "init-openbao-ssh-ca.sh").exists()
    assert (stale_boundary_dir / "local-data.txt").read_text(encoding="utf-8") == "preserve existing target data", "Deployment sync must preserve pre-existing target data"
    assert (target_dir / "scripts" / "orchestrator.py").exists()
    assert (target_dir / "scripts" / "init-semaphore.sh").exists()
    assert (target_dir / "scripts" / "healthcheck.sh").exists()
    assert (target_dir / "scripts" / "migrate-semaphore-postgres-to-sqlite.py").exists()
    assert (target_dir / "docs" / "control-plane" / "semaphore-postgres-to-sqlite.md").exists()
    assert (target_dir / ".env").read_text(encoding="utf-8") == "SEMAPHORE_ACCESS_KEY_ENCRYPTION=live-secret\nEXPOSE_PORTS=true\n", "Production .env must be preserved during sync"

    # 2. Non-production / dev / test / git files MUST NOT exist in target
    assert not (target_dir / ".git").exists(), ".git directory must NOT be copied"
    assert not (target_dir / "tests").exists(), "tests directory must NOT be copied"
    assert not (target_dir / "docs" / "adr").exists(), "Architecture docs must NOT be copied"
    assert not (target_dir / "scripts" / "validate-specs.py").exists(), "validate-specs.py must NOT be in production"
    assert not (target_dir / ".pytest_cache").exists(), ".pytest_cache must NOT be copied"

    ports_disabled_target = tmp_path / "ports_disabled"
    ports_disabled_target.mkdir()
    (ports_disabled_target / ".env").write_text("EXPOSE_PORTS=false\n", encoding="utf-8")
    (ports_disabled_target / "semaphore").mkdir()
    (ports_disabled_target / "semaphore" / "compose.override.yml").write_text("stale binding\n", encoding="utf-8")
    orchestrator.deploy_to_target(source_dir=root_dir, target_dir=ports_disabled_target)
    assert not (ports_disabled_target / "semaphore" / "compose.override.yml").exists(), "EXPOSE_PORTS=false must stay disabled after sync"


def test_ctrl_008_makefile_target_support(root_dir):
    """[CTRL-008] Makefile supports TARGET_DIR and install/production targets"""
    makefile = root_dir / "Makefile"
    content = makefile.read_text(encoding="utf-8")
    assert "TARGET_DIR" in content or "INSTALL_DIR" in content, "Makefile must support TARGET_DIR override"
