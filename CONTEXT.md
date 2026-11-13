# Overseer Domain Context

## 1. Overview
**Overseer** is a Docker Compose control plane for small-to-medium IDC infrastructure, combining OpenBao SSH CA/secrets with Semaphore UI GitOps automation.

## 2. Core Concepts & Vocabulary
- **Control Plane**: OpenBao (SSH CA and secrets) plus Semaphore UI (Ansible GitOps orchestrator). Semaphore persists its state in a local SQLite database by default.
- **GitOps Orchestration**: Semaphore UI pulling and executing idempotent playbooks from remote `node-provisioner` repository.
- **Zero-Trust Access**: Replacing static root passwords and long-lived keys with short-lived certificates signed by the OpenBao SSH CA.
- **Multi-OS Support**: Provisioning and management support across RHEL/CentOS generations (CentOS 6 to Rocky Linux 9/10) as well as Debian/Ubuntu.

## 3. System Boundaries
- `compose.yml`: Top-level orchestration for OpenBao and Semaphore UI.
- `docs/`: Unified documentation repository containing control plane specifications and ADRs (`docs/adr/`).
- `openbao/`: OpenBao configuration and SSH CA bootstrap scripts.
- `scripts/`: Bootstrap, healthcheck, specification verification, and Semaphore auto-seeding automation.
- `tests/`: End-to-end integration test suite validating Control Plane health, SSH CA signing, and GitOps orchestration.

