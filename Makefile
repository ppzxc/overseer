.PHONY: help up down restart status bootstrap init-vault init-boundary ansible-provision ansible-check test lint clean

# Default Target
help:
	@echo "================================================================================"
	@echo "                      Overseer Infrastructure Control Plane                     "
	@echo "================================================================================"
	@echo "  make bootstrap         - Full bootstrap (Compose up + Vault init + Boundary init)"
	@echo "  make up                - Start Docker Compose services in background"
	@echo "  make down              - Stop and remove Docker Compose services"
	@echo "  make restart           - Restart all control plane services"
	@echo "  make status            - Check health of Vault, Boundary, DB, Prometheus"
	@echo "  make logs              - View Docker Compose logs"
	@echo "--------------------------------------------------------------------------------"
	@echo "  make ansible-provision - Run baseline provisioning for all IDC nodes"
	@echo "  make ansible-check     - Dry-run simulation (--check --diff) on IDC nodes"
	@echo "  make spec-check        - Validate 3-way consistency (Docs <-> Code <-> Tests)"
	@echo "  make lint              - Run 3-way spec validation and ansible-lint"
	@echo "  make test              - Run Molecule integration tests in containers"
	@echo "  make test-e2e          - Run Pytest E2E System Integration Tests (Full Stack)"
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

init-vault:
	@docker compose exec vault /bin/sh /vault/scripts/init-vault-ssh-ca.sh

init-boundary:
	@docker compose run --rm --entrypoint /bin/sh boundary-controller -c "/boundary/scripts/init-boundary.sh"

spec-check:
	@./scripts/validate-specs.py


ansible-provision:
	@cd ansible && ./docker-run.sh playbooks/provision.yml

ansible-check:
	@cd ansible && ./docker-run.sh playbooks/provision.yml --check --diff

test: spec-check
	@cd ansible && ./docker-run.sh molecule test

test-e2e:
	@./scripts/run-e2e-tests.sh

lint: spec-check
	@cd ansible && ./docker-run.sh ansible-lint

clean:
	@docker compose down -v


