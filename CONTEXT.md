# Overseer Domain Context

## 1. Overview
**Overseer** is a central control plane (Docker Compose) for secure, standardized management of small-to-medium IDC server infrastructure with integrated Zero-Trust access and GitOps automation.

## 2. Core Concepts & Vocabulary
- **Control Plane**: Central services including OpenBao (SSH CA & Secrets), HashiCorp Boundary (Zero-Trust IAM), PostgreSQL (Backend DB), and Semaphore UI (GitOps Ansible Web Orchestrator).
- **GitOps Orchestration**: Semaphore UI pulling and executing idempotent playbooks from remote `node-provisioner` repository.
- **Zero-Trust Access**: Eliminating static root passwords/keys in favor of short-lived certificates signed by OpenBao SSH CA or Boundary proxied sessions.
- **Multi-OS Support**: Provisioning and management support across RHEL/CentOS generations (CentOS 6 to Rocky Linux 9/10) as well as Debian/Ubuntu.

## 3. System Boundaries
- `compose.yml`: Top-level orchestration for all control plane containers (OpenBao, Boundary, Semaphore, PostgreSQL).
- `docs/`: Unified documentation repository containing control plane specifications and ADRs (`docs/adr/`).
- `openbao/` & `boundary/`: Service-specific configuration files and bootstrap/init scripts.
- `scripts/`: Bootstrap, healthcheck, specification verification, and Semaphore auto-seeding automation.
- `tests/`: End-to-end integration test suite validating Control Plane health, SSH CA signing, and GitOps orchestration.

