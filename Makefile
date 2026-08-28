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

# Unified Actions
up bootstrap:
	@./scripts/overseer.sh start all

down:
	@./scripts/overseer.sh stop all

restart:
	@./scripts/overseer.sh restart all

status:
	@./scripts/overseer.sh status

logs:
	@./scripts/overseer.sh logs all

# OpenBao Actions
start-openbao:
	@./scripts/overseer.sh start openbao

stop-openbao:
	@./scripts/overseer.sh stop openbao

restart-openbao:
	@./scripts/overseer.sh restart openbao

init-openbao:
	@./scripts/overseer.sh init openbao

# Boundary Actions
start-boundary:
	@./scripts/overseer.sh start boundary

stop-boundary:
	@./scripts/overseer.sh stop boundary

restart-boundary:
	@./scripts/overseer.sh restart boundary

init-boundary:
	@./scripts/overseer.sh init boundary

# Semaphore Actions
start-semaphore:
	@./scripts/overseer.sh start semaphore

stop-semaphore:
	@./scripts/overseer.sh stop semaphore

restart-semaphore:
	@./scripts/overseer.sh restart semaphore

init-semaphore:
	@./scripts/overseer.sh init semaphore

# PostgreSQL Actions
start-postgres:
	@./scripts/overseer.sh start postgres

stop-postgres:
	@./scripts/overseer.sh stop postgres

restart-postgres:
	@./scripts/overseer.sh restart postgres

init-postgres:
	@./scripts/overseer.sh init postgres

# Testing & Verification
spec-check:
	@./scripts/validate-specs.py

test: spec-check test-e2e

test-e2e:
	@./scripts/run-e2e-tests.sh

clean:
	@docker compose down -v
