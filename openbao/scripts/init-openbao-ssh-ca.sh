#!/usr/bin/env bash
set -e

# ==============================================================================
# Overseer OpenBao Initialization & SSH CA Setup Script
# ==============================================================================

BAO_ADDR="${BAO_ADDR:-http://127.0.0.1:8200}"
export BAO_ADDR

echo "[*] Connecting to OpenBao at ${BAO_ADDR}..."

# OpenBao 준비 대기
until curl -s "${BAO_ADDR}/v1/sys/health" >/dev/null 2>&1 || [ $? -eq 2 ]; do
    echo "[-] Waiting for OpenBao server to start..."
    sleep 2
done

# 1. 초기화 여부 점검
INIT_STATUS=$(curl -s "${BAO_ADDR}/v1/sys/init" | jq -r '.initialized')

if [ "${INIT_STATUS}" != "true" ]; then
    echo "[*] Initializing OpenBao..."
    INIT_RESP=$(curl -s -X POST "${BAO_ADDR}/v1/sys/init" -d '{"secret_shares": 1, "secret_threshold": 1}')
    
    ROOT_TOKEN=$(echo "${INIT_RESP}" | jq -r '.root_token')
    UNSEAL_KEY=$(echo "${INIT_RESP}" | jq -r '.keys[0]')
    
    mkdir -p /openbao/data
    echo "${INIT_RESP}" > /openbao/data/openbao-init.json
    echo "[+] OpenBao initialized. Keys saved to /openbao/data/openbao-init.json"
    
    # 2. 언실(Unseal)
    echo "[*] Unsealing OpenBao..."
    curl -s -X POST "${BAO_ADDR}/v1/sys/unseal" -d "{\"key\": \"${UNSEAL_KEY}\"}" >/dev/null
else
    echo "[*] OpenBao is already initialized."
    if [ -f "/openbao/data/openbao-init.json" ]; then
        ROOT_TOKEN=$(jq -r '.root_token' /openbao/data/openbao-init.json)
        UNSEAL_KEY=$(jq -r '.keys[0]' /openbao/data/openbao-init.json)
        # 언실 시도
        curl -s -X POST "${BAO_ADDR}/v1/sys/unseal" -d "{\"key\": \"${UNSEAL_KEY}\"}" >/dev/null 2>&1 || true
    fi
fi

if [ -z "${BAO_TOKEN}" ] && [ -n "${ROOT_TOKEN}" ]; then
    export BAO_TOKEN="${ROOT_TOKEN}"
fi

echo "[+] OpenBao is unsealed and ready. Token: ${BAO_TOKEN:0:10}..."

# 3. SSH Client Signer Engine 활성화
echo "[*] Configuring SSH Certificate Authority (CA)..."
if ! curl -s -H "X-Vault-Token: ${BAO_TOKEN}" "${BAO_ADDR}/v1/sys/mounts" | jq -e '."ssh-client-signer/"' >/dev/null 2>&1; then
    echo "[*] Mounting ssh secrets engine at ssh-client-signer..."
    curl -s -X POST -H "X-Vault-Token: ${BAO_TOKEN}" \
         "${BAO_ADDR}/v1/sys/mounts/ssh-client-signer" \
         -d '{"type": "ssh"}' >/dev/null

    echo "[*] Generating SSH CA KeyPair..."
    curl -s -X POST -H "X-Vault-Token: ${BAO_TOKEN}" \
         "${BAO_ADDR}/v1/ssh-client-signer/config/ca" \
         -d '{"generate_signing_key": true}' >/dev/null
fi

# 4. SSH CA 공개키 추출 및 저장
CA_PUBLIC_KEY=$(curl -s -H "X-Vault-Token: ${BAO_TOKEN}" "${BAO_ADDR}/v1/ssh-client-signer/public_key")
echo "${CA_PUBLIC_KEY}" > /openbao/data/openbao-ssh-ca.pub
echo "[+] OpenBao SSH CA Public Key extracted to /openbao/data/openbao-ssh-ca.pub:"
echo "--------------------------------------------------------------------------------"
echo "${CA_PUBLIC_KEY}"
echo "--------------------------------------------------------------------------------"

# 5. 엔지니어 서명 역할(Role) 생성
echo "[*] Creating SSH client signer role: infra-admin-role..."
curl -s -X POST -H "X-Vault-Token: ${BAO_TOKEN}" \
     "${BAO_ADDR}/v1/ssh-client-signer/roles/infra-admin-role" \
     -d '{
       "allow_user_certificates": true,
       "allowed_users": "infra-admin,ansible,root,ppzxc",
       "allowed_extensions": "permit-pty,permit-port-forwarding,permit-agent-forwarding",
       "default_extensions": {"permit-pty": ""},
       "default_user": "infra-admin",
       "ttl": "8h",
       "max_ttl": "24h"
     }' >/dev/null

echo "[+] OpenBao SSH CA & Role setup completed successfully!"
