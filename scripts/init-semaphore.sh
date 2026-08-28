#!/usr/bin/env bash
set -e

# ==============================================================================
# Overseer Semaphore UI Auto-Initialization & Blueprint Seeder Script
# Automatically configures Project, Key Store, Repository, Inventory & Templates
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${SCRIPT_DIR}"

SEMAPHORE_ADDR="${SEMAPHORE_ADDR:-http://127.0.0.1:3000}"
SEMAPHORE_ADMIN="${SEMAPHORE_ADMIN:-admin}"
SEMAPHORE_ADMIN_PASSWORD="${SEMAPHORE_ADMIN_PASSWORD:-semaphoreadmin}"

echo "[*] Connecting to Semaphore UI at ${SEMAPHORE_ADDR}..."

# 1. Semaphore 서비스 대기
MAX_RETRIES=30
COUNT=0
until curl -s "${SEMAPHORE_ADDR}/api/ping" >/dev/null 2>&1 || curl -s "${SEMAPHORE_ADDR}/" >/dev/null 2>&1; do
    COUNT=$((COUNT+1))
    if [ ${COUNT} -ge ${MAX_RETRIES} ]; then
        echo "[-] Semaphore UI did not become ready in time. Skipping auto-seed."
        exit 0
    fi
    echo "[-] Waiting for Semaphore UI to be ready (${COUNT}/${MAX_RETRIES})..."
    sleep 2
done

COOKIE_JAR=$(mktemp)
trap 'rm -f "${COOKIE_JAR}"' EXIT

# 2. Semaphore 로그인 & 세션 쿠키 획득
echo "[*] Authenticating with Semaphore UI..."
LOGIN_STATUS=$(curl -s -c "${COOKIE_JAR}" -o /dev/null -w "%{http_code}" \
    -X POST "${SEMAPHORE_ADDR}/api/auth/login" \
    -H "Content-Type: application/json" \
    -d "{\"auth\": \"${SEMAPHORE_ADMIN}\", \"password\": \"${SEMAPHORE_ADMIN_PASSWORD}\"}")

if [ "${LOGIN_STATUS}" != "204" ] && [ "${LOGIN_STATUS}" != "200" ]; then
    echo "[-] Semaphore login failed (HTTP ${LOGIN_STATUS}). Skipping auto-seed."
    exit 0
fi

echo "[+] Authenticated successfully."

# 3. Project 조회 또는 생성 ("Overseer Infrastructure")
PROJECT_NAME="Overseer Infrastructure"
PROJECTS_JSON=$(curl -s -b "${COOKIE_JAR}" "${SEMAPHORE_ADDR}/api/projects")
PROJECT_ID=$(echo "${PROJECTS_JSON}" | jq -r ".[] | select(.name == \"${PROJECT_NAME}\") | .id" 2>/dev/null || true)

if [ -z "${PROJECT_ID}" ] || [ "${PROJECT_ID}" == "null" ]; then
    echo "[*] Creating Project '${PROJECT_NAME}'..."
    NEW_PROJECT=$(curl -s -b "${COOKIE_JAR}" -X POST "${SEMAPHORE_ADDR}/api/projects" \
        -H "Content-Type: application/json" \
        -d "{\"name\": \"${PROJECT_NAME}\", \"alert\": false}")
    PROJECT_ID=$(echo "${NEW_PROJECT}" | jq -r '.id')
    echo "[+] Created Project ID: ${PROJECT_ID}"
else
    echo "[*] Project '${PROJECT_NAME}' already exists (ID: ${PROJECT_ID})."
fi

if [ -z "${PROJECT_ID}" ] || [ "${PROJECT_ID}" == "null" ]; then
    echo "[-] Failed to obtain Project ID. Skipping auto-seed."
    exit 0
fi

# 4. Key Store 등록 (Host SSH Key / None Key)
KEYS_JSON=$(curl -s -b "${COOKIE_JAR}" "${SEMAPHORE_ADDR}/api/project/${PROJECT_ID}/keys")
KEY_ID=$(echo "${KEYS_JSON}" | jq -r '.[] | select(.name == "Local / Default SSH") | .id' 2>/dev/null || true)

if [ -z "${KEY_ID}" ] || [ "${KEY_ID}" == "null" ]; then
    echo "[*] Registering Default SSH Key in Key Store..."
    NEW_KEY=$(curl -s -b "${COOKIE_JAR}" -X POST "${SEMAPHORE_ADDR}/api/project/${PROJECT_ID}/keys" \
        -H "Content-Type: application/json" \
        -d '{"name": "Local / Default SSH", "type": "none"}')
    KEY_ID=$(echo "${NEW_KEY}" | jq -r '.id')
fi

# 5. Repository 등록 (로컬 /ansible 볼륨)
REPOS_JSON=$(curl -s -b "${COOKIE_JAR}" "${SEMAPHORE_ADDR}/api/project/${PROJECT_ID}/repositories")
REPO_ID=$(echo "${REPOS_JSON}" | jq -r '.[] | select(.name == "Overseer Local Ansible") | .id' 2>/dev/null || true)

if [ -z "${REPO_ID}" ] || [ "${REPO_ID}" == "null" ]; then
    echo "[*] Registering Local Repository in Semaphore..."
    NEW_REPO=$(curl -s -b "${COOKIE_JAR}" -X POST "${SEMAPHORE_ADDR}/api/project/${PROJECT_ID}/repositories" \
        -H "Content-Type: application/json" \
        -d "{\"name\": \"Overseer Local Ansible\", \"git_url\": \"file:///ansible\", \"git_branch\": \"main\", \"ssh_key_id\": ${KEY_ID}}")
    REPO_ID=$(echo "${NEW_REPO}" | jq -r '.id')
    echo "[+] Registered Repository ID: ${REPO_ID}"
fi

# 6. Inventory 등록 (/ansible/inventory/hosts.yml)
INV_JSON=$(curl -s -b "${COOKIE_JAR}" "${SEMAPHORE_ADDR}/api/project/${PROJECT_ID}/inventory")
INV_ID=$(echo "${INV_JSON}" | jq -r '.[] | select(.name == "IDC Hosts Inventory") | .id' 2>/dev/null || true)

if [ -z "${INV_ID}" ] || [ "${INV_ID}" == "null" ]; then
    echo "[*] Registering Inventory in Semaphore..."
    NEW_INV=$(curl -s -b "${COOKIE_JAR}" -X POST "${SEMAPHORE_ADDR}/api/project/${PROJECT_ID}/inventory" \
        -H "Content-Type: application/json" \
        -d "{\"name\": \"IDC Hosts Inventory\", \"type\": \"file\", \"inventory\": \"inventory/hosts.yml\", \"ssh_key_id\": ${KEY_ID}}")
    INV_ID=$(echo "${NEW_INV}" | jq -r '.id')
    echo "[+] Registered Inventory ID: ${INV_ID}"
fi

# 7. Environment 등록 (기본 환경 변수)
ENV_JSON=$(curl -s -b "${COOKIE_JAR}" "${SEMAPHORE_ADDR}/api/project/${PROJECT_ID}/environment")
ENV_ID=$(echo "${ENV_JSON}" | jq -r '.[] | select(.name == "Default Environment") | .id' 2>/dev/null || true)

if [ -z "${ENV_ID}" ] || [ "${ENV_ID}" == "null" ]; then
    echo "[*] Registering Default Environment..."
    NEW_ENV=$(curl -s -b "${COOKIE_JAR}" -X POST "${SEMAPHORE_ADDR}/api/project/${PROJECT_ID}/environment" \
        -H "Content-Type: application/json" \
        -d '{"name": "Default Environment", "json": "{\"ANSIBLE_FORCE_COLOR\": \"True\", \"BAO_ADDR\": \"http://openbao:8200\"}"}')
    ENV_ID=$(echo "${NEW_ENV}" | jq -r '.id')
fi

# 8. Task Templates 등록 함수
create_template_if_missing() {
    local TPL_NAME="$1"
    local PLAYBOOK="$2"
    local DESC="$3"
    local EXTRA_ARGS="$4"

    local TPLS_JSON=$(curl -s -b "${COOKIE_JAR}" "${SEMAPHORE_ADDR}/api/project/${PROJECT_ID}/templates")
    local EXISTING_ID=$(echo "${TPLS_JSON}" | jq -r ".[] | select(.name == \"${TPL_NAME}\") | .id" 2>/dev/null || true)

    if [ -z "${EXISTING_ID}" ] || [ "${EXISTING_ID}" == "null" ]; then
        echo "[*] Creating Task Template: ${TPL_NAME}..."
        local PAYLOAD=$(jq -n \
            --arg name "${TPL_NAME}" \
            --arg desc "${DESC}" \
            --arg playbook "${PLAYBOOK}" \
            --argjson repo_id "${REPO_ID}" \
            --argjson inv_id "${INV_ID}" \
            --argjson env_id "${ENV_ID}" \
            --arg extra "${EXTRA_ARGS}" \
            '{
                name: $name,
                description: $desc,
                playbook: $playbook,
                repository_id: $repo_id,
                inventory_id: $inv_id,
                environment_id: $env_id,
                arguments: (if $extra != "" then $extra else null end)
            }')
        curl -s -b "${COOKIE_JAR}" -X POST "${SEMAPHORE_ADDR}/api/project/${PROJECT_ID}/templates" \
            -H "Content-Type: application/json" \
            -d "${PAYLOAD}" >/dev/null
        echo "[+] Template created: ${TPL_NAME}"
    else
        echo "[*] Template '${TPL_NAME}' already exists."
    fi
}

# 9. 주요 플레이북 템플릿 일괄 등록
echo "[*] Seeding Ansible Task Templates..."
create_template_if_missing "1. Provision Target Servers" "playbooks/provision_servers.yml" "Baseline provisioning for IDC target servers (SSH CA + Boundary + OTEL)" ""
create_template_if_missing "2. Provision Overseer Control Plane" "playbooks/provision_overseer.yml" "Host setup for Overseer Control Plane node (Docker CE + Hardening)" ""
create_template_if_missing "3. Provision Full Stack (All)" "playbooks/provision.yml" "Full-stack provisioning for all managed nodes and overseer host" ""
create_template_if_missing "4. Regular Maintenance & Patching" "playbooks/maintenance.yml" "Routine OS security patching and telemetry agent update" ""
create_template_if_missing "5. Dry-Run Check & Diff (Simulation)" "playbooks/provision.yml" "Dry-run simulation to preview changes without modifying servers" "--check --diff"

echo "[+] Semaphore UI auto-seeding completed successfully!"
