.PHONY: help up down restart status logs bootstrap preflight \
        start-openbao stop-openbao restart-openbao init-openbao \
        start-semaphore stop-semaphore restart-semaphore init-semaphore \
        configure-seal production-sync spec-check test test-e2e clean

# Default Target
help:
	@echo "================================================================================"
	@echo "                      Overseer Infrastructure Control Plane                     "
	@echo "================================================================================"
	@echo "  make preflight                - Run pre-flight checks (tools, permissions, ports)"
	@echo "  make up / bootstrap           - Start & bootstrap all Control Plane components"
	@echo "                                  (supports TARGET_DIR=/opt/services/overseer)"
	@echo "  make production-sync          - Sync only production-critical operational files"
	@echo "  make configure-seal           - Apply KMS seal/unseal profile (local / gcpkms)"
	@echo "  make down                     - Stop all Control Plane components"
	@echo "  make restart                  - Restart all Control Plane components"
	@echo "  make status                   - Check health of OpenBao and Semaphore"
	@echo "  make logs                     - View live logs of all services"
	@echo "--------------------------------------------------------------------------------"
	@echo "  Individual Service Management (OpenBao, Semaphore):"
	@echo "  make start-<service>          - Start individual service (e.g. make start-openbao)"
	@echo "  make stop-<service>           - Stop individual service (e.g. make stop-openbao)"
	@echo "  make restart-<service>        - Restart individual service (e.g. make restart-semaphore)"
	@echo "  make init-<service>           - Run component init (e.g. make init-openbao)"
	@echo "--------------------------------------------------------------------------------"
	@echo "  make spec-check               - Validate 3-way consistency (Docs <-> Code <-> Tests)"
	@echo "  make test / test-e2e          - Run Pytest E2E System Integration Tests"
	@echo "================================================================================"

# ------------------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------------------
TARGET_DIR ?=
TARGET_FLAG := $(if $(TARGET_DIR),--target-dir $(TARGET_DIR),)

env-file:
	@if [ ! -f .env ]; then ./scripts/orchestrator.py configure-seal >/dev/null 2>&1 || cp .env.example .env; fi

configure-seal: env-file
	@./scripts/orchestrator.py configure-seal

# ------------------------------------------------------------------------------
# Full Stack (Unified)
# ------------------------------------------------------------------------------
preflight:
	@./scripts/orchestrator.py preflight

up bootstrap: env-file
	@./scripts/orchestrator.py bootstrap $(TARGET_FLAG)

production-sync: env-file
	@./scripts/orchestrator.py deploy-target $(TARGET_FLAG)

down:
	@docker compose down --remove-orphans

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
	@docker compose up -d --remove-orphans openbao
	@./scripts/orchestrator.py init-openbao

stop-openbao:
	@docker compose stop openbao

restart-openbao:
	@docker compose restart openbao

init-openbao: env-file configure-seal
	@./scripts/orchestrator.py init-openbao

# ------------------------------------------------------------------------------
# Semaphore
# ------------------------------------------------------------------------------
start-semaphore: env-file
	@docker compose up -d --remove-orphans semaphore
	@./scripts/orchestrator.py init-semaphore

stop-semaphore:
	@docker compose stop semaphore

restart-semaphore:
	@docker compose restart semaphore

init-semaphore: env-file
	@./scripts/orchestrator.py init-semaphore

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
