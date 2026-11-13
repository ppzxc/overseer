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
ANSIBLE_REPO_URL="${ANSIBLE_REPO_URL:-https://github.com/ppzxc/node-provisioner.git}"
ANSIBLE_REPO_BRANCH="${ANSIBLE_REPO_BRANCH:-main}"

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

# 5. Repository 등록 (GitOps 원격 Git 레포지토리 연동)
REPOS_JSON=$(curl -s -b "${COOKIE_JAR}" "${SEMAPHORE_ADDR}/api/project/${PROJECT_ID}/repositories")
REPO_ID=$(echo "${REPOS_JSON}" | jq -r '.[] | select(.name == "Node Provisioner GitOps") | .id' 2>/dev/null || true)

if [ -z "${REPO_ID}" ] || [ "${REPO_ID}" == "null" ]; then
    echo "[*] Registering GitOps Repository (${ANSIBLE_REPO_URL}) in Semaphore..."
    NEW_REPO=$(curl -s -b "${COOKIE_JAR}" -X POST "${SEMAPHORE_ADDR}/api/project/${PROJECT_ID}/repositories" \
        -H "Content-Type: application/json" \
        -d "{\"name\": \"Node Provisioner GitOps\", \"git_url\": \"${ANSIBLE_REPO_URL}\", \"git_branch\": \"${ANSIBLE_REPO_BRANCH}\", \"ssh_key_id\": ${KEY_ID}}")
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

# 8. Remove templates that belonged to the retired control-plane workflows.
TEMPLATES_URL="${SEMAPHORE_ADDR}/api/project/${PROJECT_ID}/templates"
TPLS_JSON=$(curl -s -b "${COOKIE_JAR}" "${TEMPLATES_URL}")
while IFS=$'\t' read -r TEMPLATE_ID TEMPLATE_NAME; do
    [ -n "${TEMPLATE_ID}" ] || continue
    echo "[*] Removing retired Task Template: ${TEMPLATE_NAME}..."
    curl -s -b "${COOKIE_JAR}" -X DELETE "${TEMPLATES_URL}/${TEMPLATE_ID}" >/dev/null
done < <(echo "${TPLS_JSON}" | jq -r '.[] | select(.name == "2. Provision Overseer Control Plane" or .name == "3. Provision Full Stack (All)") | [.id, .name] | @tsv')

# 9. Reconcile Task Templates with the current GitOps playbooks.
reconcile_template() {
    local TPL_NAME="$1"
    local PLAYBOOK="$2"
    local DESC="$3"
    local EXTRA_ARGS="$4"
    local LEGACY_NAME="${5:-}"

    local TPLS_JSON=$(curl -s -b "${COOKIE_JAR}" "${TEMPLATES_URL}")
    local EXISTING=$(echo "${TPLS_JSON}" | jq -c --arg name "${TPL_NAME}" --arg legacy "${LEGACY_NAME}" '.[] | select(.name == $name or ($legacy != "" and .name == $legacy))' | head -n 1)
    local TEMPLATE_FIELDS=$(jq -n \
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

    if [ -z "${EXISTING}" ]; then
        echo "[*] Creating Task Template: ${TPL_NAME}..."
        local PAYLOAD="${TEMPLATE_FIELDS}"
        curl -s -b "${COOKIE_JAR}" -X POST "${TEMPLATES_URL}" \
            -H "Content-Type: application/json" \
            -d "${PAYLOAD}" >/dev/null
        echo "[+] Template created: ${TPL_NAME}"
    else
        local EXISTING_ID=$(echo "${EXISTING}" | jq -r '.id')
        local PAYLOAD=$(echo "${EXISTING}" | jq --argjson fields "${TEMPLATE_FIELDS}" '. + $fields')
        echo "[*] Updating Task Template: ${TPL_NAME} (ID: ${EXISTING_ID})..."
        curl -s -b "${COOKIE_JAR}" -X PUT "${TEMPLATES_URL}/${EXISTING_ID}" \
            -H "Content-Type: application/json" \
            -d "${PAYLOAD}" >/dev/null
        echo "[+] Template reconciled: ${TPL_NAME}"
    fi
}

# 10. 주요 플레이북 템플릿 일괄 등록
echo "[*] Seeding Ansible Task Templates..."
reconcile_template "1. Provision Target Servers" "playbooks/provision_servers.yml" "Baseline provisioning for IDC target servers (OpenBao SSH CA + OTEL)" ""
reconcile_template "2. Regular Maintenance & Patching" "playbooks/maintenance.yml" "Routine OS security patching and telemetry agent update" "" "4. Regular Maintenance & Patching"
reconcile_template "3. Dry-Run Check & Diff (Simulation)" "playbooks/provision_servers.yml" "Dry-run simulation to preview changes without modifying servers" "--check --diff" "5. Dry-Run Check & Diff (Simulation)"

echo "[+] Semaphore UI auto-seeding completed successfully!"
