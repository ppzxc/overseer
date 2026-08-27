"""
E2E Test 02: OpenBao SSH CA & Key Signing Workflow
Verifies that OpenBao SSH CA is active, generates valid CA public keys, and signs user certificates.
"""

import pytest
import requests
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

def test_bao_ctrl_002_ssh_ca_mount_and_key(http_session, openbao_url):
    """[BAO-CTRL-002] OpenBao SSH CA Secrets Engine Mount and public key generation"""
    resp = http_session.get(f"{openbao_url}/v1/ssh-client-signer/public_key")
    assert resp.status_code == 200, "Failed to retrieve OpenBao SSH CA public key"
    ca_pub = resp.text.strip()
    assert ca_pub.startswith("ssh-rsa") or ca_pub.startswith("ssh-ed25519"), f"Invalid CA public key format: {ca_pub[:30]}..."

def test_bao_ctrl_003_signing_role(http_session, openbao_url, openbao_token):
    """[BAO-CTRL-003] OpenBao SSH User Certificate Signing Role and issuance"""
    if not openbao_token:
        pytest.skip("OpenBao token not available for signing test")
        
    headers = {"X-Vault-Token": openbao_token}
    
    # 1. 서명 역할(Role) 확인
    role_resp = http_session.get(f"{openbao_url}/v1/ssh-client-signer/roles/infra-admin-role", headers=headers)
    assert role_resp.status_code == 200, "infra-admin-role does not exist in OpenBao"
    
    # 2. 임시 RSA 키페어 생성
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key_openssh = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.OpenSSH,
        format=serialization.PublicFormat.OpenSSH
    ).decode("utf-8")
    
    # 3. OpenBao에 서명 요청
    sign_payload = {
        "public_key": public_key_openssh,
        "valid_principals": "infra-admin",
        "ttl": "1h"
    }
    sign_resp = http_session.post(
        f"{openbao_url}/v1/ssh-client-signer/sign/infra-admin-role",
        headers=headers,
        json=sign_payload
    )
    assert sign_resp.status_code == 200, f"OpenBao failed to sign SSH key: {sign_resp.text}"
    signed_cert = sign_resp.json().get("data", {}).get("signed_key", "")
    assert "-cert-v01@openssh.com" in signed_cert, "Signed certificate does not have valid OpenSSH Certificate format"
