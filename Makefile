.PHONY: help up down restart status bootstrap init-openbao init-boundary ansible-provision ansible-provision-overseer ansible-provision-servers ansible-check test test-all test-molecule test-e2e spec-check lint clean

# Default Target
help:
	@echo "================================================================================"
	@echo "                      Overseer Infrastructure Control Plane                     "
	@echo "================================================================================"
	@echo "  make bootstrap                  - Full bootstrap (Compose up + OpenBao init + Boundary init)"
	@echo "  make up                         - Start Docker Compose services in background"
	@echo "  make down                       - Stop and remove Docker Compose services"
	@echo "  make restart                    - Restart all control plane services"
	@echo "  make status                     - Check health of OpenBao, Boundary, PostgreSQL"
	@echo "  make logs                       - View Docker Compose logs"
	@echo "--------------------------------------------------------------------------------"
	@echo "  make ansible-provision          - Run full provisioning (overseer + servers)"
	@echo "  make ansible-provision-overseer - Run provisioning for Overseer Control Plane host"
	@echo "  make ansible-provision-servers  - Run baseline provisioning for IDC target servers"
	@echo "  make ansible-check              - Dry-run simulation (--check --diff)"
	@echo "  make spec-check                 - Validate 3-way consistency (Docs <-> Code <-> Tests)"
	@echo "  make lint                       - Run 3-way spec validation and ansible-lint"
	@echo "  make test                       - Run ALL tests (Spec + Lint + Molecule + Pytest E2E)"
	@echo "  make test-molecule              - Run Molecule integration tests in containers"
	@echo "  make test-e2e                   - Run Pytest E2E System Integration Tests (Full Stack)"
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

ansible-provision:
	@cd ansible && ./docker-run.sh playbooks/provision.yml

ansible-provision-overseer:
	@cd ansible && ./docker-run.sh playbooks/provision_overseer.yml

ansible-provision-servers:
	@cd ansible && ./docker-run.sh playbooks/provision_servers.yml

ansible-check:
	@cd ansible && ./docker-run.sh playbooks/provision.yml --check --diff

test:
	@./scripts/run-all-tests.sh

test-all: test

test-molecule: spec-check
	@cd ansible && ./docker-run.sh molecule test

test-e2e:
	@./scripts/run-e2e-tests.sh

lint: spec-check
	@cd ansible && ./docker-run.sh ansible-lint

clean:
	@docker compose down -v
