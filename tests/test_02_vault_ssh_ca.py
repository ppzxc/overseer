"""
E2E Test 02: HashiCorp Vault SSH CA & Key Signing Workflow
Verifies that Vault SSH CA is active, generates valid CA public keys, and signs user certificates.
"""

import pytest
import requests
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

def test_vault_ctrl_002_ssh_ca_mount_and_key(http_session, vault_url):
    """[VAULT-CTRL-002] Vault SSH CA Secrets Engine Mount and public key generation"""
    resp = http_session.get(f"{vault_url}/v1/ssh-client-signer/public_key")
    assert resp.status_code == 200, "Failed to retrieve Vault SSH CA public key"
    ca_pub = resp.text.strip()
    assert ca_pub.startswith("ssh-rsa") or ca_pub.startswith("ssh-ed25519"), f"Invalid CA public key format: {ca_pub[:30]}..."

def test_vault_ctrl_003_signing_role(http_session, vault_url, vault_token):
    """[VAULT-CTRL-003] Vault SSH User Certificate Signing Role and issuance"""
    if not vault_token:
        pytest.skip("Vault token not available for signing test")
        
    headers = {"X-Vault-Token": vault_token}
    
    # 1. 서명 역할(Role) 확인
    role_resp = http_session.get(f"{vault_url}/v1/ssh-client-signer/roles/infra-admin-role", headers=headers)
    assert role_resp.status_code == 200, "infra-admin-role does not exist in Vault"
    
    # 2. 임시 RSA 키페어 생성
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key_openssh = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.OpenSSH,
        format=serialization.PublicFormat.OpenSSH
    ).decode("utf-8")
    
    # 3. Vault에 서명 요청
    sign_payload = {
        "public_key": public_key_openssh,
        "valid_principals": "infra-admin",
        "ttl": "1h"
    }
    sign_resp = http_session.post(
        f"{vault_url}/v1/ssh-client-signer/sign/infra-admin-role",
        headers=headers,
        json=sign_payload
    )
    assert sign_resp.status_code == 200, f"Vault failed to sign SSH key: {sign_resp.text}"
    signed_cert = sign_resp.json().get("data", {}).get("signed_key", "")
    assert "-cert-v01@openssh.com" in signed_cert, "Signed certificate does not have valid OpenSSH Certificate format"
