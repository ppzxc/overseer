.PHONY: help up down restart status logs bootstrap \
        start-openbao stop-openbao restart-openbao init-openbao \
        start-boundary stop-boundary restart-boundary init-boundary \
        start-semaphore stop-semaphore restart-semaphore init-semaphore \
        start-postgres stop-postgres restart-postgres init-postgres \
        spec-check test test-e2e clean

# Default Target
help:
	@echo "================================================================================"
	@echo "                      Overseer Infrastructure Control Plane                     "
	@echo "================================================================================"
	@echo "  make up / bootstrap           - Start & bootstrap all Control Plane components"
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

# ------------------------------------------------------------------------------
# Full Stack (Unified)
# ------------------------------------------------------------------------------
up bootstrap: env-file init-postgres ensure-semaphore-db init-boundary init-openbao
	@echo "[*] Launching remaining services (Boundary & Semaphore)..."
	@docker compose up -d boundary-controller boundary-worker semaphore
	@$(MAKE) init-semaphore
	@echo ""
	@echo "================================================================================"
	@echo "  Overseer Control Plane is UP and READY!"
	@echo "  - OpenBao Web UI:     http://localhost:8200"
	@echo "  - Boundary Admin UI:  http://localhost:9200"
	@echo "  - Semaphore Web UI:   http://localhost:3000 (admin / semaphoreadmin)"
	@echo "================================================================================"

down:
	@docker compose down

restart:
	@docker compose restart

status:
	@./scripts/healthcheck.sh

logs:
	@docker compose logs -f

# ------------------------------------------------------------------------------
# OpenBao
# ------------------------------------------------------------------------------
start-openbao: env-file
	@docker compose up -d openbao
	@$(MAKE) init-openbao

stop-openbao:
	@docker compose stop openbao

restart-openbao:
	@docker compose restart openbao

init-openbao: env-file
	@docker compose up -d openbao
	@until curl -s "http://127.0.0.1:8200/v1/sys/health" >/dev/null 2>&1 || [ $$? -eq 2 ]; do sleep 2; done
	@docker compose exec -T openbao /bin/sh /openbao/scripts/init-openbao-ssh-ca.sh || true

# ------------------------------------------------------------------------------
# Boundary
# ------------------------------------------------------------------------------
start-boundary: env-file init-postgres
	@docker compose up -d boundary-controller boundary-worker

stop-boundary:
	@docker compose stop boundary-controller boundary-worker

restart-boundary:
	@docker compose restart boundary-controller boundary-worker

init-boundary: env-file init-postgres
	@docker compose run --rm --entrypoint /bin/sh boundary-controller -c "/boundary/scripts/init-boundary.sh" || true

# ------------------------------------------------------------------------------
# Semaphore
# ------------------------------------------------------------------------------
start-semaphore: env-file init-postgres ensure-semaphore-db
	@docker compose up -d semaphore
	@$(MAKE) init-semaphore

stop-semaphore:
	@docker compose stop semaphore

restart-semaphore:
	@docker compose restart semaphore

init-semaphore: env-file
	@./scripts/init-semaphore.sh || true

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
