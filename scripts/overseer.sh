#!/usr/bin/env bash
set -e

# ==============================================================================
# Overseer Control Plane Unified CLI Control Script
# Usage: ./scripts/overseer.sh [ACTION] [SERVICE]
#   ACTIONS:  start | stop | restart | status | init | logs
#   SERVICES: all | openbao | boundary | semaphore | postgres
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${SCRIPT_DIR}"

ACTION="${1:-help}"
SERVICE="${2:-all}"

# .env 준비
if [ ! -f ".env" ]; then
    echo "[*] Creating .env from .env.example..."
    cp .env.example .env
fi

# ------------------------------------------------------------------------------
# Helper Functions
# ------------------------------------------------------------------------------

wait_for_postgres() {
    echo "[*] Waiting for PostgreSQL to be ready..."
    until docker compose exec -T postgres pg_isready -U "${POSTGRES_USER:-boundary}" >/dev/null 2>&1; do
        sleep 2
    done
    echo "[+] PostgreSQL is healthy."
}

ensure_semaphore_db() {
    wait_for_postgres
    echo "[*] Ensuring Semaphore database exists in PostgreSQL..."
    docker compose exec -T postgres psql -U "${POSTGRES_USER:-boundary}" -d postgres -tc "SELECT 1 FROM pg_database WHERE datname = 'semaphore'" | grep -q 1 || \
    docker compose exec -T postgres psql -U "${POSTGRES_USER:-boundary}" -d postgres -c "CREATE DATABASE semaphore;" >/dev/null 2>&1 || true
}

# ------------------------------------------------------------------------------
# Init Handlers
# ------------------------------------------------------------------------------

init_postgres() {
    echo "[*] Initializing PostgreSQL backend..."
    docker compose up -d postgres
    wait_for_postgres
}

init_openbao() {
    echo "[*] Initializing OpenBao server & SSH CA..."
    docker compose up -d openbao
    until curl -s "http://127.0.0.1:8200/v1/sys/health" >/dev/null 2>&1 || [ $? -eq 2 ]; do
        sleep 2
    done
    docker compose exec -T openbao /bin/sh /openbao/scripts/init-openbao-ssh-ca.sh || true
}

init_boundary() {
    echo "[*] Initializing Boundary database schema..."
    init_postgres
    docker compose run --rm --entrypoint /bin/sh boundary-controller -c "/boundary/scripts/init-boundary.sh" || true
}

init_semaphore() {
    echo "[*] Initializing Semaphore UI and auto-seeding GitOps templates..."
    ensure_semaphore_db
    docker compose up -d semaphore
    ./scripts/init-semaphore.sh || true
}

init_all() {
    echo "================================================================================"
    echo "          Bootstrapping All Overseer Control Plane Components                   "
    echo "================================================================================"
    init_postgres
    ensure_semaphore_db
    init_boundary
    init_openbao
    docker compose up -d boundary-controller boundary-worker semaphore
    init_semaphore
    echo ""
    echo "================================================================================"
    echo "  Overseer Control Plane is UP and READY!"
    echo "  - OpenBao Web UI:     http://localhost:8200"
    echo "  - Boundary Admin UI:  http://localhost:9200"
    echo "  - Semaphore Web UI:   http://localhost:3000 (admin / semaphoreadmin)"
    echo "================================================================================"
}

# ------------------------------------------------------------------------------
# Start Handlers (with Auto-Init)
# ------------------------------------------------------------------------------

start_service() {
    case "$1" in
        postgres)
            docker compose up -d postgres
            wait_for_postgres
            ;;
        openbao)
            docker compose up -d openbao
            init_openbao
            ;;
        boundary)
            init_postgres
            docker compose up -d boundary-controller boundary-worker
            ;;
        semaphore)
            init_postgres
            ensure_semaphore_db
            docker compose up -d semaphore
            init_semaphore
            ;;
        all)
            init_all
            ;;
        *)
            echo "[-] Unknown service: $1"
            echo "    Available services: all | openbao | boundary | semaphore | postgres"
            exit 1
            ;;
    esac
}

# ------------------------------------------------------------------------------
# Stop Handlers
# ------------------------------------------------------------------------------

stop_service() {
    case "$1" in
        postgres)
            echo "[*] Stopping PostgreSQL..."
            docker compose stop postgres
            ;;
        openbao)
            echo "[*] Stopping OpenBao..."
            docker compose stop openbao
            ;;
        boundary)
            echo "[*] Stopping Boundary Controller & Worker..."
            docker compose stop boundary-controller boundary-worker
            ;;
        semaphore)
            echo "[*] Stopping Semaphore UI..."
            docker compose stop semaphore
            ;;
        all)
            echo "[*] Stopping all Overseer services..."
            docker compose down
            ;;
        *)
            echo "[-] Unknown service: $1"
            exit 1
            ;;
    esac
}

# ------------------------------------------------------------------------------
# Restart Handlers
# ------------------------------------------------------------------------------

restart_service() {
    case "$1" in
        postgres)
            docker compose restart postgres
            ;;
        openbao)
            docker compose restart openbao
            ;;
        boundary)
            docker compose restart boundary-controller boundary-worker
            ;;
        semaphore)
            docker compose restart semaphore
            ;;
        all)
            docker compose restart
            ;;
        *)
            echo "[-] Unknown service: $1"
            exit 1
            ;;
    esac
}

# ------------------------------------------------------------------------------
# Status Handler
# ------------------------------------------------------------------------------

check_status() {
    ./scripts/healthcheck.sh
}

# ------------------------------------------------------------------------------
# Main Entrypoint
# ------------------------------------------------------------------------------

case "${ACTION}" in
    start)
        start_service "${SERVICE}"
        ;;
    stop)
        stop_service "${SERVICE}"
        ;;
    restart)
        restart_service "${SERVICE}"
        ;;
    status)
        check_status
        ;;
    init)
        case "${SERVICE}" in
            postgres)  init_postgres ;;
            openbao)   init_openbao ;;
            boundary)  init_boundary ;;
            semaphore) init_semaphore ;;
            all)       init_all ;;
            *) echo "[-] Unknown service for init: ${SERVICE}"; exit 1 ;;
        esac
        ;;
    logs)
        if [ "${SERVICE}" == "all" ]; then
            docker compose logs -f
        elif [ "${SERVICE}" == "boundary" ]; then
            docker compose logs -f boundary-controller boundary-worker
        else
            docker compose logs -f "${SERVICE}"
        fi
        ;;
    help|--help|-h)
        echo "================================================================================"
        echo "          Overseer Control Plane Unified Management CLI                         "
        echo "================================================================================"
        echo "Usage: ./scripts/overseer.sh [ACTION] [SERVICE]"
        echo ""
        echo "Actions:"
        echo "  start   [all|openbao|boundary|semaphore|postgres]  - Start service(s) with auto-init"
        echo "  stop    [all|openbao|boundary|semaphore|postgres]  - Stop service(s)"
        echo "  restart [all|openbao|boundary|semaphore|postgres]  - Restart service(s)"
        echo "  init    [all|openbao|boundary|semaphore|postgres]  - Run component initialization"
        echo "  status                                             - Check overall system health"
        echo "  logs    [all|openbao|boundary|semaphore|postgres]  - Follow service container logs"
        echo "================================================================================"
        ;;
    *)
        echo "[-] Unknown action: ${ACTION}. Run './scripts/overseer.sh help' for usage."
        exit 1
        ;;
esac
