#!/usr/bin/env bash
set -e

# ==============================================================================
# Overseer Vault Initialization & SSH CA Setup Script
# ==============================================================================

VAULT_ADDR="${VAULT_ADDR:-http://127.0.0.1:8200}"
export VAULT_ADDR

echo "[*] Connecting to Vault at ${VAULT_ADDR}..."

# Vault 준비 대기
until curl -s "${VAULT_ADDR}/v1/sys/health" >/dev/null 2>&1 || [ $? -eq 2 ]; do
    echo "[-] Waiting for Vault server to start..."
    sleep 2
done

# 1. 초기화 여부 점검
INIT_STATUS=$(curl -s "${VAULT_ADDR}/v1/sys/init" | jq -r '.initialized')

if [ "${INIT_STATUS}" != "true" ]; then
    echo "[*] Initializing Vault..."
    INIT_RESP=$(curl -s -X POST "${VAULT_ADDR}/v1/sys/init" -d '{"secret_shares": 1, "secret_threshold": 1}')
    
    ROOT_TOKEN=$(echo "${INIT_RESP}" | jq -r '.root_token')
    UNSEAL_KEY=$(echo "${INIT_RESP}" | jq -r '.keys[0]')
    
    mkdir -p /vault/data
    echo "${INIT_RESP}" > /vault/data/vault-init.json
    echo "[+] Vault initialized. Keys saved to /vault/data/vault-init.json"
    
    # 2. 언실(Unseal)
    echo "[*] Unsealing Vault..."
    curl -s -X POST "${VAULT_ADDR}/v1/sys/unseal" -d "{\"key\": \"${UNSEAL_KEY}\"}" >/dev/null
else
    echo "[*] Vault is already initialized."
    if [ -f "/vault/data/vault-init.json" ]; then
        ROOT_TOKEN=$(jq -r '.root_token' /vault/data/vault-init.json)
        UNSEAL_KEY=$(jq -r '.keys[0]' /vault/data/vault-init.json)
        # 언실 시도
        curl -s -X POST "${VAULT_ADDR}/v1/sys/unseal" -d "{\"key\": \"${UNSEAL_KEY}\"}" >/dev/null 2>&1 || true
    fi
fi

if [ -z "${VAULT_TOKEN}" ] && [ -n "${ROOT_TOKEN}" ]; then
    export VAULT_TOKEN="${ROOT_TOKEN}"
fi

echo "[+] Vault is unsealed and ready. Token: ${VAULT_TOKEN:0:10}..."

# 3. SSH Client Signer Engine 활성화
echo "[*] Configuring SSH Certificate Authority (CA)..."
if ! curl -s -H "X-Vault-Token: ${VAULT_TOKEN}" "${VAULT_ADDR}/v1/sys/mounts" | jq -e '."ssh-client-signer/"' >/dev/null 2>&1; then
    echo "[*] Mounting ssh secrets engine at ssh-client-signer..."
    curl -s -X POST -H "X-Vault-Token: ${VAULT_TOKEN}" \
         "${VAULT_ADDR}/v1/sys/mounts/ssh-client-signer" \
         -d '{"type": "ssh"}' >/dev/null

    echo "[*] Generating SSH CA KeyPair..."
    curl -s -X POST -H "X-Vault-Token: ${VAULT_TOKEN}" \
         "${VAULT_ADDR}/v1/ssh-client-signer/config/ca" \
         -d '{"generate_signing_key": true}' >/dev/null
fi

# 4. SSH CA 공개키 추출 및 저장
CA_PUBLIC_KEY=$(curl -s -H "X-Vault-Token: ${VAULT_TOKEN}" "${VAULT_ADDR}/v1/ssh-client-signer/public_key")
echo "${CA_PUBLIC_KEY}" > /vault/data/vault-ssh-ca.pub
echo "[+] Vault SSH CA Public Key extracted to /vault/data/vault-ssh-ca.pub:"
echo "--------------------------------------------------------------------------------"
echo "${CA_PUBLIC_KEY}"
echo "--------------------------------------------------------------------------------"

# 5. 엔지니어 서명 역할(Role) 생성
echo "[*] Creating SSH client signer role: infra-admin-role..."
curl -s -X POST -H "X-Vault-Token: ${VAULT_TOKEN}" \
     "${VAULT_ADDR}/v1/ssh-client-signer/roles/infra-admin-role" \
     -d '{
       "allow_user_certificates": true,
       "allowed_users": "infra-admin,ansible,root,ppzxc",
       "allowed_extensions": "permit-pty,permit-port-forwarding,permit-agent-forwarding",
       "default_extensions": {"permit-pty": ""},
       "default_user": "infra-admin",
       "ttl": "8h",
       "max_ttl": "24h"
     }' >/dev/null

echo "[+] Vault SSH CA & Role setup completed successfully!"
