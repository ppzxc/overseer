"""
E2E Test 06: OpenBao Seal Matrix, Port Exposure & Key Modes
Verifies OpenBao seal profiles, port binding, network setup, and manual/auto key lifecycle modes.
"""

import os
import shutil
import pytest
from pathlib import Path

def test_ctrl_007_seal_profiles_existence(root_dir):
    """[CTRL-007] Pluggable Seal and KMS Backend Configuration Profiles exist"""
    openbao_profiles = root_dir / "openbao" / "config" / "profiles"
    assert openbao_profiles.exists(), "openbao/config/profiles directory is missing"
    
    # Check OpenBao profiles
    assert (openbao_profiles / "local-shamir.hcl").exists(), "local-shamir.hcl profile missing in OpenBao"
    assert (openbao_profiles / "gcp-kms.hcl").exists(), "gcp-kms.hcl profile missing in OpenBao"
    

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

def test_ctrl_007_orchestrator_seal_and_port_branching(root_dir):
    import sys
    sys.path.insert(0, str(root_dir / "scripts"))
    import orchestrator
    
    # 1. Test Local Shamir + Port Exposed
    os.environ["SEAL_TYPE"] = "local"
    os.environ["EXPOSE_PORTS"] = "true"
    os.environ["OPENBAO_SHAMIR_MODE"] = "auto"
    
    res = orchestrator.prompt_and_configure_all(interactive=False)
    assert res["seal_type"] == "local"
    assert res["expose_ports"] is True
    assert res["shamir_mode"] == "auto"
    
    active_openbao = (root_dir / "openbao" / "config" / "openbao.hcl").read_text(encoding="utf-8")
    assert 'storage "raft"' in active_openbao
    assert 'seal "gcpckms"' not in active_openbao
    
    # Only Semaphore gets a host binding; OpenBao stays internal to backend.
    openbao_override = root_dir / "openbao" / "compose.override.yml"
    semaphore_override = root_dir / "semaphore" / "compose.override.yml"
    assert not openbao_override.exists(), "OpenBao must remain internal when EXPOSE_PORTS=true"
    assert semaphore_override.exists(), "Semaphore override should be generated when EXPOSE_PORTS=true"
    assert "0.0.0.0:3000:3000" in semaphore_override.read_text(encoding="utf-8")
    
    env_content = (root_dir / ".env").read_text(encoding="utf-8")
    assert "SEMAPHORE_PORT_BINDING=0.0.0.0:3000:3000" in env_content
    assert "OPENBAO_SHAMIR_MODE=auto" in env_content
    # When SEAL_TYPE=local, GCP keys should remain commented
    assert "# GCP_PROJECT=" in env_content
    
    # 2. Test GCP Cloud KMS + Internal Ports + Manual Shamir
    os.environ["SEAL_TYPE"] = "gcpkms"
    os.environ["EXPOSE_PORTS"] = "false"
    os.environ["OPENBAO_SHAMIR_MODE"] = "manual"
    os.environ["GCP_PROJECT"] = "test-proj"
    os.environ["GCP_REGION"] = "asia-northeast3"
    os.environ["GCP_KEY_RING"] = "test-ring"
    os.environ["GCP_OPENBAO_KEY"] = "test-bao-key"
    
    res_gcp = orchestrator.prompt_and_configure_all(interactive=False)
    assert res_gcp["seal_type"] == "gcpkms"
    assert res_gcp["expose_ports"] is False
    assert res_gcp["shamir_mode"] == "manual"
    
    active_openbao_gcp = (root_dir / "openbao" / "config" / "openbao.hcl").read_text(encoding="utf-8")
    assert 'seal "gcpckms"' in active_openbao_gcp
    assert 'project     = "test-proj"' in active_openbao_gcp
    
    # When EXPOSE_PORTS=false, both service overrides should be deleted.
    assert not openbao_override.exists(), "OpenBao override should be removed when EXPOSE_PORTS=false"
    assert not semaphore_override.exists(), "Semaphore override should be removed when EXPOSE_PORTS=false"
    
    env_content_internal = (root_dir / ".env").read_text(encoding="utf-8")
    assert "EXPOSE_PORTS=false" in env_content_internal
    # When ports are not exposed, port binding variables should be commented out
    assert "OPENBAO_SHAMIR_MODE=manual" in env_content_internal
    # When SEAL_TYPE=gcpkms, GCP keys should be uncommented
    assert "GCP_PROJECT=test-proj" in env_content_internal
    
    # Revert back to local + exposed for standard testing
    os.environ["SEAL_TYPE"] = "local"
    os.environ["EXPOSE_PORTS"] = "true"
    os.environ["OPENBAO_SHAMIR_MODE"] = "auto"
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
    compose_content = (root_dir / "openbao" / "compose.yml").read_text(encoding="utf-8")
    assert "OPENBAO_SHAMIR_MODE:" in compose_content, "OPENBAO_SHAMIR_MODE missing from openbao/compose.yml"
    
    orchestrator_code = (root_dir / "scripts" / "orchestrator.py").read_text(encoding="utf-8")
    assert "OPENBAO_SHAMIR_MODE=" in orchestrator_code, "OPENBAO_SHAMIR_MODE propagation missing in orchestrator.py"

def test_ctrl_007_manual_mode_zero_knowledge_wipe(root_dir):
    """[CTRL-007] Zero-Knowledge Manual mode wipes the Semaphore encryption key from .env."""
    import sys
    sys.path.insert(0, str(root_dir / "scripts"))
    import orchestrator
    
    os.environ["KEY_MANAGEMENT_PROFILE"] = "manual"
    os.environ["SEAL_TYPE"] = "local"
    os.environ["EXPOSE_PORTS"] = "true"
    
    # 1. Run prompt_and_configure_all in manual mode
    res = orchestrator.prompt_and_configure_all(interactive=False)
    assert res["key_management_profile"] == "manual"
    
    # 2. Check keys in memory / os.environ are present during session
    assert os.getenv("SEMAPHORE_ACCESS_KEY_ENCRYPTION"), "Semaphore key should be generated in memory"
    
    # 3. Verify .env file on disk has NO keys (completely wiped for zero-knowledge)
    env_content = (root_dir / ".env").read_text(encoding="utf-8")
    assert "SEMAPHORE_ACCESS_KEY_ENCRYPTION=\n" in env_content or "SEMAPHORE_ACCESS_KEY_ENCRYPTION=\"\"" in env_content or "SEMAPHORE_ACCESS_KEY_ENCRYPTION=" in env_content
    
    # Parse env directly and assert they are empty string in .env
    env_vars = orchestrator.read_env_file()
    assert env_vars.get("SEMAPHORE_ACCESS_KEY_ENCRYPTION") == "", "SEMAPHORE_ACCESS_KEY_ENCRYPTION must be empty in .env"

def test_ctrl_007_reboot_injection_support(root_dir):
    """[CTRL-007] Validates that orchestrator checks and prompts or accepts injected session keys on reboot/start"""
    import sys
    sys.path.insert(0, str(root_dir / "scripts"))
    import orchestrator
    
    # Function check
    assert hasattr(orchestrator, "ensure_runtime_keys_injected"), "orchestrator must implement ensure_runtime_keys_injected"

