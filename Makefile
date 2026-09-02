.PHONY: help up down restart status logs bootstrap preflight \
        start-openbao stop-openbao restart-openbao init-openbao \
        start-boundary stop-boundary restart-boundary init-boundary \
        start-semaphore stop-semaphore restart-semaphore init-semaphore \
        start-postgres stop-postgres restart-postgres init-postgres \
        configure-seal spec-check test test-e2e clean

# Default Target
help:
	@echo "================================================================================"
	@echo "                      Overseer Infrastructure Control Plane                     "
	@echo "================================================================================"
	@echo "  make preflight                - Run pre-flight checks (tools, permissions, ports)"
	@echo "  make up / bootstrap           - Start & bootstrap all Control Plane components"
	@echo "  make configure-seal           - Apply KMS seal/unseal profile (local / gcpkms)"
	@echo "  make down                     - Stop all Control Plane components"
	@echo "  make restart                  - Restart all Control Plane components"
	@echo "  make status                   - Check health of OpenBao, Boundary, Postgres, Semaphore"
	@echo "  make logs                     - View live logs of all services"
	@echo "--------------------------------------------------------------------------------"
	@echo "  Individual Service Management (OpenBao, Boundary, Semaphore, Postgres):"
	@echo "  make start-<service>          - Start individual service (e.g. make start-openbao)"
	@echo "  make stop-<service>           - Stop individual service (e.g. make stop-boundary)"
	@echo "  make restart-<service>        - Restart individual service (e.g. make restart-semaphore)"
	@echo "  make init-<service>           - Run component init (e.g. make init-openbao)"
	@echo "--------------------------------------------------------------------------------"
	@echo "  make spec-check               - Validate 3-way consistency (Docs <-> Code <-> Tests)"
	@echo "  make test / test-e2e          - Run Pytest E2E System Integration Tests"
	@echo "================================================================================"

# ------------------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------------------
env-file:
	@if [ ! -f .env ]; then cp .env.example .env; fi

wait-postgres: env-file
	@echo "[*] Waiting for PostgreSQL..."
	@until docker compose exec -T postgres pg_isready -U boundary >/dev/null 2>&1; do sleep 2; done
	@echo "[+] PostgreSQL is ready."

ensure-semaphore-db: wait-postgres
	@echo "[*] Ensuring Semaphore database exists in PostgreSQL..."
	@docker compose exec -T postgres psql -U boundary -d postgres -tc "SELECT 1 FROM pg_database WHERE datname = 'semaphore'" | grep -q 1 || \
	docker compose exec -T postgres psql -U boundary -d postgres -c "CREATE DATABASE semaphore;" >/dev/null 2>&1 || true

configure-seal: env-file
	@./scripts/orchestrator.py configure-seal

# ------------------------------------------------------------------------------
# Full Stack (Unified)
# ------------------------------------------------------------------------------
preflight:
	@./scripts/orchestrator.py preflight

up bootstrap: env-file
	@./scripts/orchestrator.py bootstrap

down:
	@docker compose down

restart:
	@docker compose restart

status:
	@./scripts/orchestrator.py status

logs:
	@docker compose logs -f

# ------------------------------------------------------------------------------
# OpenBao
# ------------------------------------------------------------------------------
start-openbao: env-file configure-seal
	@docker compose up -d openbao
	@./scripts/orchestrator.py init-openbao

stop-openbao:
	@docker compose stop openbao

restart-openbao:
	@docker compose restart openbao

init-openbao: env-file configure-seal
	@./scripts/orchestrator.py init-openbao

# ------------------------------------------------------------------------------
# Boundary
# ------------------------------------------------------------------------------
start-boundary: env-file configure-seal init-postgres
	@docker compose up -d boundary-controller boundary-worker

stop-boundary:
	@docker compose stop boundary-controller boundary-worker

restart-boundary:
	@docker compose restart boundary-controller boundary-worker

init-boundary: env-file configure-seal init-postgres
	@./scripts/orchestrator.py init-boundary

# ------------------------------------------------------------------------------
# Semaphore
# ------------------------------------------------------------------------------
start-semaphore: env-file init-postgres ensure-semaphore-db
	@docker compose up -d semaphore
	@./scripts/orchestrator.py init-semaphore

stop-semaphore:
	@docker compose stop semaphore

restart-semaphore:
	@docker compose restart semaphore

init-semaphore: env-file
	@./scripts/orchestrator.py init-semaphore

# ------------------------------------------------------------------------------
# PostgreSQL
# ------------------------------------------------------------------------------
start-postgres init-postgres: env-file
	@docker compose up -d postgres
	@$(MAKE) wait-postgres

stop-postgres:
	@docker compose stop postgres

restart-postgres:
	@docker compose restart postgres

# ------------------------------------------------------------------------------
# Testing & Verification
# ------------------------------------------------------------------------------
spec-check:
	@./scripts/validate-specs.py

test: spec-check test-e2e

test-e2e:
	@pytest tests/ -v

clean:
	@docker compose down -v
