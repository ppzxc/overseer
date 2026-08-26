# Overseer 3-Way Traceability Matrix (자동 생성)

> **최종 검증 일시**: `2026-08-26 22:31:50`  
> **검증 상태**: `✅ 100% PASS`  
> **스펙 총계**: `66` 개 (Control Plane: 11, Ansible: 55)

---

## 1. 전역 3단 정합성 검증 매트릭스

| Spec ID | 구분 (Domain) | 스펙 및 태스크 명칭 (Specification Name) | 문서 (Docs) | 코드 구현 (Implementation) | 자동화 테스트 (Verification) |
|---|---|---|:---:|:---:|:---:|
| `BND-001` | Ansible Node | Skip Boundary Target if disabled | ✅ OK | ✅ `ansible/boundary_target` | ✅ `Molecule Direct Verify` |
| `BND-002` | Ansible Node | Create Boundary target metadata directory | ✅ OK | ✅ `ansible/boundary_target` | ⚡ `Integrated in Pipeline` |
| `BND-003` | Ansible Node | Write Boundary Target Node Info | ✅ OK | ✅ `ansible/boundary_target` | ⚡ `Integrated in Pipeline` |
| `BND-CTRL-001` | Control Plane | Boundary Controller Database and API | ✅ OK | ✅ `boundary/config/controller.hcl` | ✅ `Pytest E2E (test_01_control_plane.py)` |
| `BND-CTRL-002` | Control Plane | Boundary Cluster Communications | ✅ OK | ✅ `boundary/config/controller.hcl` | ✅ `Pytest E2E (test_03_boundary.py)` |
| `BND-CTRL-003` | Control Plane | Boundary Worker Proxy Gateway | ✅ OK | ✅ `boundary/config/worker.hcl` | ✅ `Pytest E2E (test_03_boundary.py)` |
| `COMMON-001` | Ansible Node | Set timezone | ✅ OK | ✅ `ansible/common` | ✅ `Molecule Direct Verify` |
| `COMMON-002` | Ansible Node | Fix EOL CentOS 6 / 7 Vault Repositories | ✅ OK | ✅ `ansible/common` | ⚡ `Integrated in Pipeline` |
| `COMMON-003` | Ansible Node | Install common packages (Debian/Ubuntu) | ✅ OK | ✅ `ansible/common` | ⚡ `Integrated in Pipeline` |
| `COMMON-004` | Ansible Node | Install EPEL repository (RedHat/CentOS 7, Rocky 8, 9) | ✅ OK | ✅ `ansible/common` | ⚡ `Integrated in Pipeline` |
| `COMMON-005` | Ansible Node | Install common packages (RedHat/CentOS 6, 7 via YUM) | ✅ OK | ✅ `ansible/common` | ⚡ `Integrated in Pipeline` |
| `COMMON-006` | Ansible Node | Install common packages (RHEL/Rocky 8, 9, 10 via DNF) | ✅ OK | ✅ `ansible/common` | ⚡ `Integrated in Pipeline` |
| `COMMON-007` | Ansible Node | Install optional diagnostic tools (htop, iotop) | ✅ OK | ✅ `ansible/common` | ⚡ `Integrated in Pipeline` |
| `COMMON-008` | Ansible Node | Configure Chrony NTP servers (Modern OS) | ✅ OK | ✅ `ansible/common` | ✅ `Molecule Direct Verify` |
| `COMMON-009` | Ansible Node | Ensure Chrony service is running (Modern OS) | ✅ OK | ✅ `ansible/common` | ⚡ `Integrated in Pipeline` |
| `COMMON-010` | Ansible Node | Ensure NTP service is running (CentOS 6 legacy) | ✅ OK | ✅ `ansible/common` | ⚡ `Integrated in Pipeline` |
| `COMMON-011` | Ansible Node | Apply sysctl kernel tuning | ✅ OK | ✅ `ansible/common` | ✅ `Molecule Direct Verify` |
| `COMMON-012` | Ansible Node | Ensure admin user group exists | ✅ OK | ✅ `ansible/common` | ✅ `Molecule Direct Verify` |
| `COMMON-013` | Ansible Node | Ensure admin user exists with sudo privileges | ✅ OK | ✅ `ansible/common` | ✅ `Molecule Direct Verify` |
| `COMMON-014` | Ansible Node | Enable passwordless sudo for admin user | ✅ OK | ✅ `ansible/common` | ✅ `Molecule Direct Verify` |
| `COMMON-015` | Ansible Node | Deploy admin SSH public keys | ✅ OK | ✅ `ansible/common` | ✅ `Molecule Direct Verify` |
| `COMMON-016` | Ansible Node | Configure system security limits (nofile/nproc) | ✅ OK | ✅ `ansible/common` | ✅ `Molecule Direct Verify` |
| `COMMON-017` | Ansible Node | Configure Systemd Journald retention limits | ✅ OK | ✅ `ansible/common` | ✅ `Molecule Direct Verify` |
| `CTRL-001` | Control Plane | PostgreSQL Database Backend Service | ✅ OK | ✅ `docker-compose.yml` | ✅ `Pytest E2E (test_01_control_plane.py)` |
| `CTRL-002` | Control Plane | Overseer Bridge Network Isolation | ✅ OK | ✅ `docker-compose.yml` | ✅ `Pytest E2E (test_01_control_plane.py)` |
| `CTRL-003` | Control Plane | Automated Full Stack Bootstrap | ✅ OK | ✅ `scripts/bootstrap.sh` | ✅ `Pytest E2E (test_01_control_plane.py)` |
| `MON-001` | Ansible Node | Create node_exporter system group | ✅ OK | ✅ `ansible/monitoring` | ✅ `Molecule Direct Verify` |
| `MON-002` | Ansible Node | Create node_exporter system user | ✅ OK | ✅ `ansible/monitoring` | ✅ `Molecule Direct Verify` |
| `MON-003` | Ansible Node | Download and install Node Exporter binary | ✅ OK | ✅ `ansible/monitoring` | ✅ `Molecule Direct Verify` |
| `MON-004` | Ansible Node | Create systemd service for node_exporter | ✅ OK | ✅ `ansible/monitoring` | ✅ `Molecule Direct Verify` |
| `MON-005` | Ansible Node | Ensure node_exporter service is started and enabled | ✅ OK | ✅ `ansible/monitoring` | ✅ `Molecule Direct Verify` |
| `MON-006` | Ansible Node | Create otelcol system group | ✅ OK | ✅ `ansible/monitoring` | ✅ `Molecule Direct Verify` |
| `MON-007` | Ansible Node | Create otelcol system user | ✅ OK | ✅ `ansible/monitoring` | ✅ `Molecule Direct Verify` |
| `MON-008` | Ansible Node | Download and install OpenTelemetry Collector Contrib binary | ✅ OK | ✅ `ansible/monitoring` | ✅ `Molecule Direct Verify` |
| `MON-009` | Ansible Node | Deploy OpenTelemetry Collector Contrib configuration (OpenObserve OTLP pipeline) | ✅ OK | ✅ `ansible/monitoring` | ✅ `Molecule Direct Verify` |
| `MON-010` | Ansible Node | Create systemd service for otelcol-contrib | ✅ OK | ✅ `ansible/monitoring` | ✅ `Molecule Direct Verify` |
| `MON-011` | Ansible Node | Ensure otelcol-contrib service is started and enabled | ✅ OK | ✅ `ansible/monitoring` | ✅ `Molecule Direct Verify` |
| `PROM-CTRL-001` | Control Plane | Prometheus Server Health and API | ✅ OK | ✅ `docker-compose.yml` | ✅ `Pytest E2E (test_01_control_plane.py)` |
| `PROM-CTRL-002` | Control Plane | Prometheus Control Plane and Node Scrape Config | ✅ OK | ✅ `prometheus/prometheus.yml` | ✅ `Pytest E2E (test_04_ansible_e2e.py)` |
| `SEC-001` | Ansible Node | Configure SSH Hardening parameters | ✅ OK | ✅ `ansible/security` | ✅ `Molecule Direct Verify` |
| `SEC-002` | Ansible Node | Ensure UFW is installed (Debian) | ✅ OK | ✅ `ansible/security` | ⚡ `Integrated in Pipeline` |
| `SEC-003` | Ansible Node | Allow incoming TCP ports via UFW (Debian) | ✅ OK | ✅ `ansible/security` | ⚡ `Integrated in Pipeline` |
| `SEC-004` | Ansible Node | Enable UFW with default deny incoming (Debian) | ✅ OK | ✅ `ansible/security` | ⚡ `Integrated in Pipeline` |
| `SEC-005` | Ansible Node | Ensure firewalld is installed and running (RHEL/Rocky 7+) | ✅ OK | ✅ `ansible/security` | ⚡ `Integrated in Pipeline` |
| `SEC-006` | Ansible Node | Ensure firewalld service is started and enabled (RHEL/Rocky 7+) | ✅ OK | ✅ `ansible/security` | ⚡ `Integrated in Pipeline` |
| `SEC-007` | Ansible Node | Allow incoming TCP ports via firewalld (RHEL/Rocky 7+) | ✅ OK | ✅ `ansible/security` | ⚡ `Integrated in Pipeline` |
| `SEC-008` | Ansible Node | Allow incoming TCP ports via iptables (CentOS 6) | ✅ OK | ✅ `ansible/security` | ⚡ `Integrated in Pipeline` |
| `SEC-009` | Ansible Node | Install fail2ban package if available | ✅ OK | ✅ `ansible/security` | ⚡ `Integrated in Pipeline` |
| `SEC-010` | Ansible Node | Ensure fail2ban is running and enabled (if installed) | ✅ OK | ✅ `ansible/security` | ⚡ `Integrated in Pipeline` |
| `SEC-011` | Ansible Node | Configure SELinux in permissive mode (RHEL/Rocky 7+) | ✅ OK | ✅ `ansible/security` | ✅ `Molecule Direct Verify` |
| `SEC-012` | Ansible Node | Deploy Auditd security audit rules | ✅ OK | ✅ `ansible/security` | ✅ `Molecule Direct Verify` |
| `SEC-013` | Ansible Node | Ensure Auditd service is running and enabled | ✅ OK | ✅ `ansible/security` | ✅ `Molecule Direct Verify` |
| `SEC-014` | Ansible Node | Configure Sudo timestamp timeout and log file | ✅ OK | ✅ `ansible/security` | ✅ `Molecule Direct Verify` |
| `SEC-015` | Ansible Node | Deploy Fail2ban SSH jail configuration | ✅ OK | ✅ `ansible/security` | ✅ `Molecule Direct Verify` |
| `SEC-016` | Ansible Node | Restrict Node Exporter port to monitoring subnets in Firewalld (RHEL/Rocky 7+) | ✅ OK | ✅ `ansible/security` | ✅ `Molecule Direct Verify` |
| `SEC-017` | Ansible Node | Restrict Node Exporter port to monitoring subnets in UFW (Debian) | ✅ OK | ✅ `ansible/security` | ✅ `Molecule Direct Verify` |
| `VAULT-001` | Ansible Node | Skip Vault SSH CA if disabled or key is empty | ✅ OK | ✅ `ansible/vault_ssh_ca` | ✅ `Molecule Direct Verify` |
| `VAULT-002` | Ansible Node | Check OpenSSH CA capability (requires OpenSSH >= 5.4, RHEL/CentOS 7+) | ✅ OK | ✅ `ansible/vault_ssh_ca` | ⚡ `Integrated in Pipeline` |
| `VAULT-003` | Ansible Node | Ensure SSH configuration directory exists | ✅ OK | ✅ `ansible/vault_ssh_ca` | ⚡ `Integrated in Pipeline` |
| `VAULT-004` | Ansible Node | Deploy Vault SSH CA Public Key | ✅ OK | ✅ `ansible/vault_ssh_ca` | ⚡ `Integrated in Pipeline` |
| `VAULT-005` | Ansible Node | Ensure AuthorizedPrincipals directory exists | ✅ OK | ✅ `ansible/vault_ssh_ca` | ⚡ `Integrated in Pipeline` |
| `VAULT-006` | Ansible Node | Create admin user principals file | ✅ OK | ✅ `ansible/vault_ssh_ca` | ⚡ `Integrated in Pipeline` |
| `VAULT-007` | Ansible Node | Configure sshd to trust Vault CA Keys and AuthorizedPrincipals | ✅ OK | ✅ `ansible/vault_ssh_ca` | ⚡ `Integrated in Pipeline` |
| `VAULT-CTRL-001` | Control Plane | Vault Server Initialization and Unseal | ✅ OK | ✅ `vault/config/vault.hcl` | ✅ `Pytest E2E (test_01_control_plane.py)` |
| `VAULT-CTRL-002` | Control Plane | Vault SSH CA Secrets Engine Mount | ✅ OK | ✅ `vault/scripts/init-vault-ssh-ca.sh` | ✅ `Pytest E2E (test_02_vault_ssh_ca.py)` |
| `VAULT-CTRL-003` | Control Plane | Vault SSH User Certificate Signing Role | ✅ OK | ✅ `vault/scripts/init-vault-ssh-ca.sh` | ✅ `Pytest E2E (test_02_vault_ssh_ca.py)` |

---

## 2. 검증 실행 방법

```bash
# 전역 3단 정합성 자동 검증
make spec-check

# Pytest E2E 시스템 통합 테스트
make test-e2e
```
