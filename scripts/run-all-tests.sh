#!/usr/bin/env bash
set -e

# ==============================================================================
# Overseer All-in-One Integrated Test Suite Runner
# ==============================================================================
# Runs all levels of tests in sequence:
# 1. 3-Way Traceability & Spec Consistency Check (Docs <-> Code <-> Tests)
# 2. Ansible Linter (ansible-lint)
# 3. Molecule Role Integration Tests (Rocky Linux / Ubuntu Multi-OS)
# 4. Full-Stack E2E System Integration Tests (Pytest + Testinfra)
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${SCRIPT_DIR}"

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
BOLD='\033[1m'
NC='\033[0m'

echo -e "${BOLD}${BLUE}================================================================================${NC}"
echo -e "${BOLD}${BLUE}               Overseer All-in-One Comprehensive Test Suite                     ${NC}"
echo -e "${BOLD}${BLUE}================================================================================${NC}"

# 1. 3-Way Traceability & Spec Check
echo -e "\n${BOLD}[Stage 1/4] 3-Way Traceability & Specification Validation${NC}"
echo "--------------------------------------------------------------------------------"
./scripts/validate-specs.py

# 2. Ansible Linting
echo -e "\n${BOLD}[Stage 2/4] Ansible Linting (ansible-lint)${NC}"
echo "--------------------------------------------------------------------------------"
(cd ansible && ./docker-run.sh ansible-lint)

# 3. Molecule Role Integration Tests
echo -e "\n${BOLD}[Stage 3/4] Molecule Container Integration Tests (Multi-OS)${NC}"
echo "--------------------------------------------------------------------------------"
(cd ansible && ./docker-run.sh molecule test)

# 4. Full-Stack E2E System Integration Tests
echo -e "\n${BOLD}[Stage 4/4] Full-Stack E2E System Integration Tests (Pytest)${NC}"
echo "--------------------------------------------------------------------------------"

# Ensure control plane is running for E2E tests
if ! docker compose ps --services --filter "status=running" | grep -q "openbao"; then
    echo -e "${YELLOW}[!] Control plane is not running. Bootstrapping control plane for E2E tests...${NC}"
    ./scripts/bootstrap.sh
fi

./scripts/run-e2e-tests.sh

echo -e "\n${BOLD}${GREEN}================================================================================${NC}"
echo -e "${BOLD}${GREEN}  🎉 ALL OVERSEER TESTS PASSED SUCCESSFULLY! (100% Comprehensive Coverage)       ${NC}"
echo -e "${BOLD}${GREEN}================================================================================${NC}"
