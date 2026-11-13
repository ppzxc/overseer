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
    assert "--services-root" in content and "--data-root" in content
    assert "/opt/services/overseer" in content, "Default target path /opt/services/overseer missing"

def test_ctrl_008_production_sync_file_matrix(root_dir, tmp_path, monkeypatch):
    """[CTRL-008] Copy one Compose file per service and persist config under the data root."""
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
    services_root = tmp_path / "services"
    data_root = tmp_path / "data"
    for service in ("openbao", "semaphore"):
        stale = services_root / service
        stale.mkdir(parents=True)
        (stale / "stale.txt").write_text("remove stale service-folder file", encoding="utf-8")
    
    # Run deployment sync to temporary target
    copied_files = orchestrator.deploy_to_target(
        source_dir=root_dir,
        target_dir=target_dir,
        services_root=services_root,
        data_root=data_root,
    )
    
    # 1. Essential files MUST exist in target
    assert (services_root / "openbao" / "compose.yml").exists(), "OpenBao Compose file must be in its service folder"
    assert (services_root / "semaphore" / "compose.yml").exists(), "Semaphore Compose file must be in its service folder"
    assert sorted(p.name for p in (services_root / "openbao").iterdir()) == ["compose.yml"]
    assert sorted(p.name for p in (services_root / "semaphore").iterdir()) == ["compose.yml"]
    assert (target_dir / "semaphore.compose.override.yml").exists(), "Optional port binding must live outside the service folder"
    assert not (target_dir / "compose.yml").exists(), "combined root Compose file must not be deployed"
    assert not (target_dir / "compose.override.yml").exists(), "obsolete root Compose override must be removed"
    assert (target_dir / "Makefile").exists(), "Makefile must be in production target"
    assert (target_dir / "README.md").exists(), "README.md must be in production target"
    assert (target_dir / "CONTEXT.md").exists(), "CONTEXT.md must be in production target"
    assert (target_dir / "openbao" / ".env.example").exists()
    assert (target_dir / "semaphore" / ".env.example").exists()
    assert (data_root / "openbao" / "config" / "openbao.hcl").exists()
    assert (data_root / "openbao" / "config" / "profiles" / "local-shamir.hcl").exists()
    assert (target_dir / "openbao" / "config" / "profiles" / "local-shamir.hcl").exists()
    assert (data_root / "semaphore" / "config" / "requirements.txt").exists()
    assert (target_dir / "openbao" / "scripts" / "init-openbao-ssh-ca.sh").exists()
    assert (stale_boundary_dir / "local-data.txt").read_text(encoding="utf-8") == "preserve existing target data", "Deployment sync must preserve pre-existing target data"
    assert (target_dir / "scripts" / "orchestrator.py").exists()
    assert (target_dir / "scripts" / "init-semaphore.sh").exists()
    assert (target_dir / "scripts" / "healthcheck.sh").exists()
    assert (target_dir / "scripts" / "migrate-semaphore-postgres-to-sqlite.py").exists()
    assert (target_dir / "docs" / "control-plane" / "semaphore-postgres-to-sqlite.md").exists()
    assert not (target_dir / ".env").exists(), "legacy shared .env must no longer be active"
    assert (target_dir / ".env.legacy").exists(), "legacy shared .env must be retained for rollback"
    env_after_sync = (data_root / "semaphore" / "config" / ".env").read_text(encoding="utf-8")
    assert "SEMAPHORE_ACCESS_KEY_ENCRYPTION=live-secret\n" in env_after_sync
    assert "SEMAPHORE_CONFIG_DIR=" + str(data_root) + "/semaphore/config" in env_after_sync
    openbao_env_after_sync = (data_root / "openbao" / "config" / ".env").read_text(encoding="utf-8")
    assert "OPENBAO_COMPOSE_DIR=" + str(services_root) + "/openbao" in openbao_env_after_sync
    monkeypatch.setattr(orchestrator, "ROOT_DIR", target_dir)
    monkeypatch.setattr(orchestrator, "get_service_env_file", lambda service: data_root / service / "config" / ".env")
    command = orchestrator.compose_command("openbao", "ps")
    assert str(services_root / "openbao" / "compose.yml") in command
    assert str(services_root / "openbao") in command
    assert str(data_root / "openbao" / "config" / ".env") in command
    semaphore_command = orchestrator.compose_command("semaphore", "ps")
    assert str(target_dir / "semaphore.compose.override.yml") in semaphore_command
    assert str(data_root / "semaphore" / "config" / ".env") in semaphore_command

    # 2. Non-production / dev / test / git files MUST NOT exist in target
    assert not (target_dir / ".git").exists(), ".git directory must NOT be copied"
    assert not (target_dir / "tests").exists(), "tests directory must NOT be copied"
    assert not (target_dir / "docs" / "adr").exists(), "Architecture docs must NOT be copied"
    assert not (target_dir / "scripts" / "validate-specs.py").exists(), "validate-specs.py must NOT be in production"
    assert not (target_dir / ".pytest_cache").exists(), ".pytest_cache must NOT be copied"

def test_ctrl_008_makefile_target_support(root_dir):
    """[CTRL-008] Makefile supports TARGET_DIR and install/production targets"""
    makefile = root_dir / "Makefile"
    content = makefile.read_text(encoding="utf-8")
    assert "TARGET_DIR" in content or "INSTALL_DIR" in content, "Makefile must support TARGET_DIR override"
