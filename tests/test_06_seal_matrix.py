"""
E2E Test 06: Pluggable KMS Seal/Unseal Matrix, Port Exposure & Key Modes
Verifies that OpenBao and Boundary support multi-backend profiles (Local Shamir/AEAD and GCP Cloud KMS),
validates port binding configuration branching, external backend network auto-creation,
and manual/auto Shamir and AEAD lifecycle modes.
"""

import os
import shutil
import pytest
from pathlib import Path

def test_ctrl_007_seal_profiles_existence(root_dir):
    """[CTRL-007] Pluggable Seal and KMS Backend Configuration Profiles exist"""
    openbao_profiles = root_dir / "openbao" / "config" / "profiles"
    boundary_profiles = root_dir / "boundary" / "config" / "profiles"
    
    assert openbao_profiles.exists(), "openbao/config/profiles directory is missing"
    assert boundary_profiles.exists(), "boundary/config/profiles directory is missing"
    
    # Check OpenBao profiles
    assert (openbao_profiles / "local-shamir.hcl").exists(), "local-shamir.hcl profile missing in OpenBao"
    assert (openbao_profiles / "gcp-kms.hcl").exists(), "gcp-kms.hcl profile missing in OpenBao"
    
    # Check Boundary Controller & Worker profiles
    assert (boundary_profiles / "local-aead.hcl").exists(), "local-aead.hcl profile missing in Boundary"
    assert (boundary_profiles / "gcp-kms.hcl").exists(), "gcp-kms.hcl profile missing in Boundary"
    assert (boundary_profiles / "worker-local-aead.hcl").exists(), "worker-local-aead.hcl profile missing in Boundary"
    assert (boundary_profiles / "worker-gcp-kms.hcl").exists(), "worker-gcp-kms.hcl profile missing in Boundary"

def test_ctrl_007_openbao_profile_content(root_dir):
    """[CTRL-007] OpenBao Profile configurations syntax and seal backend declarations"""
    openbao_profiles = root_dir / "openbao" / "config" / "profiles"
    
    local_shamir = (openbao_profiles / "local-shamir.hcl").read_text(encoding="utf-8")
    assert 'storage "raft"' in local_shamir, "storage raft missing in local-shamir profile"
    assert 'listener "tcp"' in local_shamir, "tcp listener missing in local-shamir profile"
    assert 'seal "gcpckms"' not in local_shamir, "local-shamir should not contain gcpckms seal"
    
    gcp_kms = (openbao_profiles / "gcp-kms.hcl").read_text(encoding="utf-8")
    assert 'seal "gcpckms"' in gcp_kms, 'seal "gcpckms" block missing in gcp-kms profile'
    assert 'project' in gcp_kms and 'key_ring' in gcp_kms and 'crypto_key' in gcp_kms, "GCP KMS attributes missing in profile"

def test_ctrl_007_boundary_profile_content(root_dir):
    """[CTRL-007] Boundary Controller and Worker Profile KMS backend declarations"""
    boundary_profiles = root_dir / "boundary" / "config" / "profiles"
    
    # Local AEAD controller
    local_ctrl = (boundary_profiles / "local-aead.hcl").read_text(encoding="utf-8")
    assert 'kms "aead"' in local_ctrl, "kms aead missing in local-aead controller profile"
    assert 'purpose   = "root"' in local_ctrl
    assert 'purpose   = "worker-auth"' in local_ctrl
    assert 'purpose   = "recovery"' in local_ctrl
    assert 'purpose     = "api"' in local_ctrl, "purpose = api missing in local-aead controller"
    assert 'purpose     = "cluster"' in local_ctrl, "purpose = cluster missing in local-aead controller"
    
    # Local AEAD worker
    local_worker = (boundary_profiles / "worker-local-aead.hcl").read_text(encoding="utf-8")
    assert 'purpose     = "proxy"' in local_worker, "purpose = proxy missing in worker profile"
    
    # GCP KMS controller
    gcp_ctrl = (boundary_profiles / "gcp-kms.hcl").read_text(encoding="utf-8")
    assert 'kms "gcpckms"' in gcp_ctrl, 'kms "gcpckms" missing in gcp-kms controller profile'
    assert 'purpose    = "root"' in gcp_ctrl
    assert 'purpose    = "worker-auth"' in gcp_ctrl
    assert 'purpose    = "recovery"' in gcp_ctrl

def test_ctrl_007_orchestrator_seal_and_port_branching(root_dir):
    import sys
    sys.path.insert(0, str(root_dir / "scripts"))
    import orchestrator
    
    # 1. Test Local Shamir + Port Exposed
    os.environ["SEAL_TYPE"] = "local"
    os.environ["EXPOSE_PORTS"] = "true"
    os.environ["OPENBAO_SHAMIR_MODE"] = "auto"
    os.environ["BOUNDARY_AEAD_MODE"] = "auto"
    
    res = orchestrator.prompt_and_configure_all(interactive=False)
    assert res["seal_type"] == "local"
    assert res["expose_ports"] is True
    assert res["shamir_mode"] == "auto"
    assert res["aead_mode"] == "auto"
    
    active_openbao = (root_dir / "openbao" / "config" / "openbao.hcl").read_text(encoding="utf-8")
    assert 'storage "raft"' in active_openbao
    assert 'seal "gcpckms"' not in active_openbao
    
    env_content = (root_dir / ".env").read_text(encoding="utf-8")
    assert "OPENBAO_PORT_BINDING=8200:8200" in env_content
    assert "SEMAPHORE_PORT_BINDING=3000:3000" in env_content
    assert "OPENBAO_SHAMIR_MODE=auto" in env_content
    
    # 2. Test GCP Cloud KMS + Internal Ports + Manual Shamir
    os.environ["SEAL_TYPE"] = "gcpkms"
    os.environ["EXPOSE_PORTS"] = "false"
    os.environ["OPENBAO_SHAMIR_MODE"] = "manual"
    os.environ["BOUNDARY_AEAD_MODE"] = "manual"
    os.environ["GCP_PROJECT"] = "test-proj"
    os.environ["GCP_REGION"] = "asia-northeast3"
    os.environ["GCP_KEY_RING"] = "test-ring"
    os.environ["GCP_OPENBAO_KEY"] = "test-bao-key"
    os.environ["GCP_BOUNDARY_ROOT_KEY"] = "test-bnd-root"
    os.environ["GCP_BOUNDARY_WORKER_AUTH_KEY"] = "test-bnd-worker"
    os.environ["GCP_BOUNDARY_RECOVERY_KEY"] = "test-bnd-recovery"
    
    res_gcp = orchestrator.prompt_and_configure_all(interactive=False)
    assert res_gcp["seal_type"] == "gcpkms"
    assert res_gcp["expose_ports"] is False
    assert res_gcp["shamir_mode"] == "manual"
    assert res_gcp["aead_mode"] == "manual"
    
    active_openbao_gcp = (root_dir / "openbao" / "config" / "openbao.hcl").read_text(encoding="utf-8")
    assert 'seal "gcpckms"' in active_openbao_gcp
    assert 'project     = "test-proj"' in active_openbao_gcp
    
    env_content_internal = (root_dir / ".env").read_text(encoding="utf-8")
    assert "EXPOSE_PORTS=false" in env_content_internal
    assert "OPENBAO_PORT_BINDING=127.0.0.1::8200" in env_content_internal
    assert "OPENBAO_SHAMIR_MODE=manual" in env_content_internal
    
    # Revert back to local + exposed for standard testing
    os.environ["SEAL_TYPE"] = "local"
    os.environ["EXPOSE_PORTS"] = "true"
    os.environ["OPENBAO_SHAMIR_MODE"] = "auto"
    os.environ["BOUNDARY_AEAD_MODE"] = "auto"
    orchestrator.prompt_and_configure_all(interactive=False)

def test_ctrl_007_openbao_init_script_unseal_branching(root_dir):
    """[CTRL-007] OpenBao Initialization script supports both Auto and Manual Shamir modes & Cloud KMS"""
    init_script = (root_dir / "openbao" / "scripts" / "init-openbao-ssh-ca.sh").read_text(encoding="utf-8")
    
    assert "SHAMIR_MODE" in init_script, "SHAMIR_MODE variable missing in init-openbao-ssh-ca.sh"
    assert "MANUAL Key Management Mode" in init_script or "manual" in init_script, "Manual mode prompt missing in init-openbao-ssh-ca.sh"
    assert "rm -f /openbao/data/openbao-init.json" in init_script, "Manual mode must delete persisted init file"
    assert "recovery_keys" in init_script, "recovery_keys parsing missing in init-openbao-ssh-ca.sh"
    assert "sys/seal-status" in init_script, "seal-status checking missing in init-openbao-ssh-ca.sh"
    
    # Verify Compose and Orchestrator bindings
    compose_content = (root_dir / "compose.yml").read_text(encoding="utf-8")
    assert "OPENBAO_SHAMIR_MODE:" in compose_content, "OPENBAO_SHAMIR_MODE missing from compose.yml"
    
    orchestrator_code = (root_dir / "scripts" / "orchestrator.py").read_text(encoding="utf-8")
    assert "OPENBAO_SHAMIR_MODE=" in orchestrator_code, "OPENBAO_SHAMIR_MODE propagation missing in orchestrator.py"
