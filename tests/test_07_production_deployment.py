"""
E2E Test 07: Production Deployment & Backup-Ready Sync Pipeline
Verifies that Overseer packages and syncs only production-critical operational files
to the target directory (default: /opt/services/overseer), excluding dev, tests, docs, and git files.
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
    
    # Run deployment sync to temporary target
    copied_files = orchestrator.deploy_to_target(source_dir=root_dir, target_dir=target_dir, execute_bootstrap=False)
    
    # 1. Essential files MUST exist in target
    assert (target_dir / "compose.yml").exists(), "compose.yml must be in production target"
    assert (target_dir / "Makefile").exists(), "Makefile must be in production target"
    assert (target_dir / "README.md").exists(), "README.md must be in production target"
    assert (target_dir / "CONTEXT.md").exists(), "CONTEXT.md must be in production target"
    assert (target_dir / ".env.example").exists(), ".env.example must be in production target"
    assert (target_dir / "openbao" / "config").exists()
    assert (target_dir / "openbao" / "scripts" / "init-openbao-ssh-ca.sh").exists()
    assert (target_dir / "boundary" / "config").exists()
    assert (target_dir / "boundary" / "scripts" / "init-boundary.sh").exists()
    assert (target_dir / "scripts" / "orchestrator.py").exists()
    assert (target_dir / "scripts" / "init-semaphore.sh").exists()
    assert (target_dir / "scripts" / "healthcheck.sh").exists()

    # 2. Non-production / dev / test / git files MUST NOT exist in target
    assert not (target_dir / ".git").exists(), ".git directory must NOT be copied"
    assert not (target_dir / "tests").exists(), "tests directory must NOT be copied"
    assert not (target_dir / "docs").exists(), "docs directory must NOT be copied"
    assert not (target_dir / "scripts" / "validate-specs.py").exists(), "validate-specs.py must NOT be in production"
    assert not (target_dir / ".pytest_cache").exists(), ".pytest_cache must NOT be copied"

def test_ctrl_008_makefile_target_support(root_dir):
    """[CTRL-008] Makefile supports TARGET_DIR and install/production targets"""
    makefile = root_dir / "Makefile"
    content = makefile.read_text(encoding="utf-8")
    assert "TARGET_DIR" in content or "INSTALL_DIR" in content, "Makefile must support TARGET_DIR override"
