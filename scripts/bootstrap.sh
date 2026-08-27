#!/usr/bin/env bash
set -e

# ==============================================================================
# Overseer Control Plane Full Bootstrap Script
# Starts Docker Compose, initializes Vault SSH CA, and bootstraps Boundary
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${SCRIPT_DIR}"

echo "================================================================================"
echo "          Starting Overseer Infrastructure Control Plane (Docker Compose)       "
echo "================================================================================"

# 1. .env 파일 준비
if [ ! -f ".env" ]; then
    echo "[*] Creating .env from .env.example..."
    cp .env.example .env
fi

# 2. Docker Compose 기동
echo "[*] Launching Docker Compose services (Postgres, OpenBao)..."
docker compose up -d postgres openbao

# 3. PostgreSQL 헬스 대기
echo "[*] Waiting for PostgreSQL to be ready..."
until docker compose exec -T postgres pg_isready -U boundary >/dev/null 2>&1; do
    sleep 2
done
echo "[+] PostgreSQL is healthy."

# 3-1. Semaphore Database 생성 (필요 시)
echo "[*] Ensuring Semaphore database exists in PostgreSQL..."
docker compose exec -T postgres psql -U boundary -d postgres -tc "SELECT 1 FROM pg_database WHERE datname = 'semaphore'" | grep -q 1 || \
docker compose exec -T postgres psql -U boundary -d postgres -c "CREATE DATABASE semaphore;" || true

# 4. Boundary Database 초기화 및 Controller/Worker 기동
echo "[*] Initializing Boundary database..."
docker compose run --rm --entrypoint /bin/sh boundary-controller -c "/boundary/scripts/init-boundary.sh" || true

echo "[*] Starting Boundary Controller, Worker, and Semaphore UI..."
docker compose up -d boundary-controller boundary-worker semaphore

# 5. OpenBao 초기화 & SSH CA 활성화
echo "[*] Bootstrapping OpenBao SSH CA..."
docker compose exec -T openbao /bin/sh /openbao/scripts/init-openbao-ssh-ca.sh || true

echo ""
echo "================================================================================"
echo "          Overseer Control Plane is UP and READY!                              "
echo "================================================================================"
echo "  - OpenBao Web UI:     http://localhost:8200"
echo "  - Boundary Admin UI:  http://localhost:9200"
echo "  - Semaphore Web UI:   http://localhost:3000 (admin / semaphoreadmin)"
echo "  - OpenBao SSH CA Key: openbao/data/openbao-ssh-ca.pub"
echo "================================================================================"
echo "  To provision servers with Ansible (CLI or Semaphore Web UI):"
echo "    make ansible-provision-overseer   # For Overseer Control Plane host"
echo "    make ansible-provision-servers    # For IDC Target servers"
echo "================================================================================"
