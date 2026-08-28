# Overseer Domain Context

## 1. Overview
**Overseer** is a central control plane (Docker Compose) and on-premise provisioning automation toolchain (Ansible) designed for secure, standardized management of small-to-medium IDC server infrastructure.

## 2. Core Concepts & Vocabulary
- **Control Plane**: Central services including OpenBao (SSH CA & Secrets), HashiCorp Boundary (Zero-Trust IAM), PostgreSQL (Backend DB), Semaphore UI (Ansible Web Orchestrator), and Prometheus.
- **Node Automation (Ansible)**: Idempotent roles (`common`, `security`, `docker_engine`, `overseer_control_plane`, `openbao_ssh_ca`, `boundary_target`, `monitoring`) for bootstrapping and maintaining IDC machines.
- **Zero-Trust Access**: Eliminating static root passwords/keys in favor of short-lived certificates signed by Vault SSH CA or Boundary proxied sessions.
- **Multi-OS Support**: Full support across RHEL/CentOS generations (CentOS 6 legacy to CentOS 7/8 and Rocky Linux 9/10) as well as Debian/Ubuntu.
- **Unified Observability Pipeline**: OpenTelemetry Collector Contrib (`otelcol-contrib`) utilizing `hostmetrics` receiver for hardware/OS kernel metrics, `filelog` receiver for OS security & audit logs, and OTLP forwarding to central OpenObserve.
- **Layered Security Hardening**: Permissive SELinux with audit logging, Auditd critical watchers, Fail2ban SSH jail, subnet-restricted firewalls, and custom SSH ports.


## 3. System Boundaries
- `docker-compose.yml`: Top-level orchestration for all control plane containers.
- `ansible/`: Self-contained Ansible configuration, inventory, playbooks, roles, and Molecule test scenarios.
- `docs/`: Unified documentation repository containing operational guidelines and ADRs (`docs/adr/`).
- `vault/` & `boundary/`: Service-specific configuration files and bootstrap/init scripts.

