"""
E2E Test 06: Pluggable KMS Seal/Unseal Matrix & Configuration Injection
Verifies that OpenBao and Boundary support multi-backend profiles (Local Shamir/AEAD and GCP Cloud KMS),
validates profile HCL schemas, configuration template rendering, and Orchestrator seal selection.
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
    
    # GCP KMS controller
    gcp_ctrl = (boundary_profiles / "gcp-kms.hcl").read_text(encoding="utf-8")
    assert 'kms "gcpckms"' in gcp_ctrl, 'kms "gcpckms" missing in gcp-kms controller profile'
    assert 'purpose    = "root"' in gcp_ctrl
    assert 'purpose    = "worker-auth"' in gcp_ctrl
    assert 'purpose    = "recovery"' in gcp_ctrl
    
    # Local AEAD worker
    local_worker = (boundary_profiles / "worker-local-aead.hcl").read_text(encoding="utf-8")
    assert 'kms "aead"' in local_worker and 'purpose   = "worker-auth"' in local_worker
    
    # GCP KMS worker
    gcp_worker = (boundary_profiles / "worker-gcp-kms.hcl").read_text(encoding="utf-8")
    assert 'kms "gcpckms"' in gcp_worker and 'purpose    = "worker-auth"' in gcp_worker

def test_ctrl_007_orchestrator_seal_injection(root_dir, tmp_path):
    """[CTRL-007] Orchestrator dynamic profile injection and templating mechanism"""
    import sys
    sys.path.insert(0, str(root_dir / "scripts"))
    import orchestrator
    
    # 1. Test Local Shamir injection
    os.environ["SEAL_TYPE"] = "local"
    selected = orchestrator.prompt_and_configure_seal_backend(interactive=False)
    assert selected == "local"
    
    active_openbao = (root_dir / "openbao" / "config" / "openbao.hcl").read_text(encoding="utf-8")
    assert 'seal "gcpckms"' not in active_openbao
    
    active_boundary = (root_dir / "boundary" / "config" / "controller.hcl").read_text(encoding="utf-8")
    assert 'kms "aead"' in active_boundary
    
    # 2. Test GCP KMS injection with environment variables
    os.environ["SEAL_TYPE"] = "gcpkms"
    os.environ["GCP_PROJECT"] = "test-project-123"
    os.environ["GCP_REGION"] = "asia-northeast3"
    os.environ["GCP_KEY_RING"] = "test-ring"
    os.environ["GCP_OPENBAO_KEY"] = "test-bao-key"
    os.environ["GCP_BOUNDARY_ROOT_KEY"] = "test-bnd-root"
    os.environ["GCP_BOUNDARY_WORKER_AUTH_KEY"] = "test-bnd-worker"
    os.environ["GCP_BOUNDARY_RECOVERY_KEY"] = "test-bnd-recovery"
    
    selected_gcp = orchestrator.prompt_and_configure_seal_backend(interactive=False)
    assert selected_gcp == "gcpkms"
    
    active_openbao_gcp = (root_dir / "openbao" / "config" / "openbao.hcl").read_text(encoding="utf-8")
    assert 'seal "gcpckms"' in active_openbao_gcp
    assert 'project     = "test-project-123"' in active_openbao_gcp
    assert 'crypto_key  = "test-bao-key"' in active_openbao_gcp
    
    active_bnd_ctrl_gcp = (root_dir / "boundary" / "config" / "controller.hcl").read_text(encoding="utf-8")
    assert 'kms "gcpckms"' in active_bnd_ctrl_gcp
    assert 'project    = "test-project-123"' in active_bnd_ctrl_gcp
    assert 'crypto_key = "test-bnd-root"' in active_bnd_ctrl_gcp
    
    active_bnd_worker_gcp = (root_dir / "boundary" / "config" / "worker.hcl").read_text(encoding="utf-8")
    assert 'kms "gcpckms"' in active_bnd_worker_gcp
    assert 'crypto_key = "test-bnd-worker"' in active_bnd_worker_gcp
    
    # Revert back to local profile for standard testing
    os.environ["SEAL_TYPE"] = "local"
    orchestrator.prompt_and_configure_seal_backend(interactive=False)

def test_ctrl_007_openbao_init_script_unseal_branching(root_dir):
    """[CTRL-007] OpenBao Initialization script supports both Shamir Unseal and Auto-Unseal Recovery keys"""
    init_script = (root_dir / "openbao" / "scripts" / "init-openbao-ssh-ca.sh").read_text(encoding="utf-8")
    
    assert "recovery_keys" in init_script, "recovery_keys parsing missing in init-openbao-ssh-ca.sh"
    assert "Auto-Unseal" in init_script or "keys | length" in init_script, "Auto-unseal branching logic missing in init-openbao-ssh-ca.sh"
    assert "sys/seal-status" in init_script, "seal-status checking missing in init-openbao-ssh-ca.sh"
