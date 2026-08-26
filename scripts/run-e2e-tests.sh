#!/usr/bin/env bash
set -e

# ==============================================================================
# Overseer E2E System Integration Test Runner (Pytest + Testinfra)
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${SCRIPT_DIR}"

echo "================================================================================"
echo "          Running Overseer E2E System Integration Tests (Pytest)                "
echo "================================================================================"

# 가상환경 또는 pytest 확인
if command -v pytest >/dev/null 2>&1; then
    pytest tests/ -v "$@"
else
    # Docker 컨테이너(overseer-ansible) 내부에서 pytest 실행
    echo "[*] Running pytest inside overseer-ansible container..."
    cd ansible && ./docker-run.sh pytest /ansible/../tests/ -v "$@"
fi
