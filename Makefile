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
	@echo "  make up / bootstrap           - Start and initialize both service Compose projects"
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
SERVICES_ROOT ?= /opt/services
DATA_ROOT ?= /data

env-file:
	@if [ ! -f .env ]; then ./scripts/orchestrator.py configure-seal >/dev/null 2>&1 || cp .env.example .env; fi

configure-seal: env-file
	@./scripts/orchestrator.py configure-seal

# ------------------------------------------------------------------------------
# Local Bootstrap and Production File Sync
# ------------------------------------------------------------------------------
preflight:
	@./scripts/orchestrator.py preflight

up bootstrap: env-file
	@./scripts/orchestrator.py bootstrap

production-sync: env-file
	@./scripts/orchestrator.py deploy-target $(TARGET_FLAG) --services-root $(SERVICES_ROOT) --data-root $(DATA_ROOT)

down:
	@./scripts/orchestrator.py down

restart:
	@./scripts/orchestrator.py restart-openbao
	@./scripts/orchestrator.py restart-semaphore

status:
	@./scripts/orchestrator.py status

logs:
	@./scripts/orchestrator.py logs

# ------------------------------------------------------------------------------
# OpenBao
# ------------------------------------------------------------------------------
start-openbao: env-file configure-seal
	@./scripts/orchestrator.py init-openbao

stop-openbao:
	@./scripts/orchestrator.py stop-openbao

restart-openbao:
	@./scripts/orchestrator.py restart-openbao

init-openbao: env-file configure-seal
	@./scripts/orchestrator.py init-openbao

# ------------------------------------------------------------------------------
# Semaphore
# ------------------------------------------------------------------------------
start-semaphore: env-file configure-seal
	@./scripts/orchestrator.py start-semaphore
	@./scripts/orchestrator.py init-semaphore

stop-semaphore:
	@./scripts/orchestrator.py stop-semaphore

restart-semaphore:
	@./scripts/orchestrator.py restart-semaphore

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
	@./scripts/orchestrator.py down
