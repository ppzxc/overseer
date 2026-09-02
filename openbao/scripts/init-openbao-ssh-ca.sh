#!/bin/sh
set -e

# ==============================================================================
# Overseer OpenBao Initialization & SSH CA Setup Script
# Supports:
#   - Local Shamir Auto-Unseal (persisted key)
#   - Local Shamir Manual-Unseal (ephemeral key / user input)
#   - Cloud Auto-Unseal (GCP Cloud KMS recovery keys)
# ==============================================================================

BAO_ADDR="${BAO_ADDR:-http://127.0.0.1:8200}"
export BAO_ADDR
SHAMIR_MODE="${OPENBAO_SHAMIR_MODE:-auto}"

echo "[*] Connecting to OpenBao at ${BAO_ADDR}..."

# OpenBao 준비 대기 (OpenBao HTTP API 응답 대기 - 200, 501 uninit, 503 sealed 등)
until curl -s -o /dev/null "${BAO_ADDR}/v1/sys/init"; do
    echo "[-] Waiting for OpenBao server to start..."
    sleep 2
done

# 1. 초기화 여부 점검
INIT_STATUS=$(curl -s "${BAO_ADDR}/v1/sys/init" | jq -r '.initialized')

if [ "${INIT_STATUS}" != "true" ]; then
    echo "[*] Initializing OpenBao..."
    INIT_RESP=$(curl -s -X POST "${BAO_ADDR}/v1/sys/init" -d '{"secret_shares": 1, "secret_threshold": 1}')
    
    ROOT_TOKEN=$(echo "${INIT_RESP}" | jq -r '.root_token // empty')
    UNSEAL_KEY=$(echo "${INIT_RESP}" | jq -r '(.keys // .recovery_keys // [])[0] // empty')
    
    mkdir -p /openbao/data
    
    if [ "${SHAMIR_MODE}" = "manual" ]; then
        echo "================================================================================"
        echo " [IMPORTANT] OpenBao Initialized in MANUAL Key Management Mode!"
        echo " Please securely copy and backup your unseal key and root token below."
        echo " This key file will NOT be stored on disk!"
        echo "--------------------------------------------------------------------------------"
        echo " UNSEAL KEY  : ${UNSEAL_KEY}"
        echo " ROOT TOKEN  : ${ROOT_TOKEN}"
        echo "================================================================================"
        # Unseal initial instance
        curl -s -X POST "${BAO_ADDR}/v1/sys/unseal" -d "{\"key\": \"${UNSEAL_KEY}\"}" >/dev/null
    else
        echo "${INIT_RESP}" > /openbao/data/openbao-init.json
        echo "[+] OpenBao initialized. Keys saved to /openbao/data/openbao-init.json"
        
        # 2. 언실(Unseal) - Shamir 키가 존재할 때 수동 Unseal 수행
        if echo "${INIT_RESP}" | jq -e '.keys | length > 0' >/dev/null 2>&1; then
            echo "[*] Unsealing OpenBao with Shamir key..."
            curl -s -X POST "${BAO_ADDR}/v1/sys/unseal" -d "{\"key\": \"${UNSEAL_KEY}\"}" >/dev/null
        else
            echo "[+] OpenBao is configured with Auto-Unseal (Recovery keys generated). Waiting for auto-unseal..."
        fi
    fi
else
    echo "[*] OpenBao is already initialized."
    if [ -f "/openbao/data/openbao-init.json" ]; then
        ROOT_TOKEN=$(jq -r '.root_token // empty' /openbao/data/openbao-init.json)
        UNSEAL_KEY=$(jq -r '(.keys // .recovery_keys // [])[0] // empty' /openbao/data/openbao-init.json)
        
        # Shamir 키가 있는 경우 언실 시도
        if jq -e '.keys | length > 0' /openbao/data/openbao-init.json >/dev/null 2>&1; then
            curl -s -X POST "${BAO_ADDR}/v1/sys/unseal" -d "{\"key\": \"${UNSEAL_KEY}\"}" >/dev/null 2>&1 || true
        fi
    elif [ -n "${PROVIDED_UNSEAL_KEY}" ]; then
        echo "[*] Unsealing with provided unseal key..."
        curl -s -X POST "${BAO_ADDR}/v1/sys/unseal" -d "{\"key\": \"${PROVIDED_UNSEAL_KEY}\"}" >/dev/null 2>&1 || true
        ROOT_TOKEN="${BAO_TOKEN}"
    fi
fi

if [ -z "${BAO_TOKEN}" ] && [ -n "${ROOT_TOKEN}" ]; then
    export BAO_TOKEN="${ROOT_TOKEN}"
fi

# Unsealed 상태 대기 (최대 10초)
for i in $(seq 1 10); do
    SEALED_STATUS=$(curl -s "${BAO_ADDR}/v1/sys/seal-status" | jq -r '.sealed')
    if [ "${SEALED_STATUS}" = "false" ]; then
        break
    fi
    sleep 1
done

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
