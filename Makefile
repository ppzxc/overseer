.PHONY: help up down restart status logs bootstrap init-openbao init-boundary init-semaphore spec-check test test-e2e clean

# Default Target
help:
	@echo "================================================================================"
	@echo "                      Overseer Infrastructure Control Plane                     "
	@echo "================================================================================"
	@echo "  make bootstrap       - Full bootstrap (Compose up + OpenBao + Boundary + Semaphore)"
	@echo "  make up              - Start Docker Compose services in background"
	@echo "  make down            - Stop and remove Docker Compose services"
	@echo "  make restart         - Restart all control plane services"
	@echo "  make status          - Check health of OpenBao, Boundary, PostgreSQL, Semaphore"
	@echo "  make logs            - View Docker Compose logs"
	@echo "--------------------------------------------------------------------------------"
	@echo "  make init-openbao    - Initialize OpenBao and bootstrap SSH CA engine"
	@echo "  make init-boundary   - Initialize Boundary database and configuration"
	@echo "  make init-semaphore  - Seed Semaphore UI projects, repositories, and templates"
	@echo "  make spec-check      - Validate 3-way consistency (Docs <-> Code <-> Tests)"
	@echo "  make test            - Run 3-Way Spec Check and Pytest E2E Suite"
	@echo "  make test-e2e        - Run Pytest E2E System Integration Tests"
	@echo "================================================================================"

bootstrap:
	@./scripts/bootstrap.sh

up:
	@docker compose up -d

down:
	@docker compose down

restart:
	@docker compose restart

status:
	@./scripts/healthcheck.sh

logs:
	@docker compose logs -f

init-openbao:
	@docker compose exec openbao /bin/sh /openbao/scripts/init-openbao-ssh-ca.sh

init-boundary:
	@docker compose run --rm --entrypoint /bin/sh boundary-controller -c "/boundary/scripts/init-boundary.sh"

init-semaphore:
	@./scripts/init-semaphore.sh

spec-check:
	@./scripts/validate-specs.py

test: spec-check test-e2e

test-e2e:
	@./scripts/run-e2e-tests.sh

clean:
	@docker compose down -v
