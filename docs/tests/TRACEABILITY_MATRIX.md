# Overseer 3-Way Traceability Matrix (자동 생성)

> **최종 검증 일시**: `2026-08-27 16:47:51`  
> **검증 상태**: `✅ 100% PASS`  
> **스펙 총계**: `80` 개 (Control Plane: 9, Ansible: 71)

---

## 1. 전역 3단 정합성 검증 매트릭스

| Spec ID | 구분 (Domain) | 스펙 및 태스크 명칭 (Specification Name) | 문서 (Docs) | 코드 구현 (Implementation) | 자동화 테스트 (Verification) |
|---|---|---|:---:|:---:|:---:|
| `BAO-001` | Ansible Node | Skip OpenBao SSH CA if disabled or key is empty | ✅ OK | ✅ `ansible/openbao_ssh_ca` | ✅ `Molecule Direct Verify` |
| `BAO-002` | Ansible Node | Check OpenSSH CA capability (requires OpenSSH >= 5.4, RHEL/CentOS 7+) | ✅ OK | ✅ `ansible/openbao_ssh_ca` | ⚡ `Integrated in Pipeline` |
| `BAO-003` | Ansible Node | Ensure SSH configuration directory exists | ✅ OK | ✅ `ansible/openbao_ssh_ca` | ⚡ `Integrated in Pipeline` |
| `BAO-004` | Ansible Node | Deploy OpenBao SSH CA Public Key | ✅ OK | ✅ `ansible/openbao_ssh_ca` | ⚡ `Integrated in Pipeline` |
| `BAO-005` | Ansible Node | Ensure AuthorizedPrincipals directory exists | ✅ OK | ✅ `ansible/openbao_ssh_ca` | ⚡ `Integrated in Pipeline` |
| `BAO-006` | Ansible Node | Create admin user principals file | ✅ OK | ✅ `ansible/openbao_ssh_ca` | ⚡ `Integrated in Pipeline` |
| `BAO-007` | Ansible Node | Configure sshd to trust OpenBao CA Keys and AuthorizedPrincipals | ✅ OK | ✅ `ansible/openbao_ssh_ca` | ⚡ `Integrated in Pipeline` |
| `BAO-CTRL-001` | Control Plane | OpenBao Server Initialization and Unseal | ✅ OK | ✅ `openbao/config/openbao.hcl` | ✅ `Pytest E2E (test_01_control_plane.py)` |
| `BAO-CTRL-002` | Control Plane | OpenBao SSH CA Secrets Engine Mount | ✅ OK | ✅ `openbao/scripts/init-openbao-ssh-ca.sh` | ✅ `Pytest E2E (test_02_openbao_ssh_ca.py)` |
| `BAO-CTRL-003` | Control Plane | OpenBao SSH User Certificate Signing Role | ✅ OK | ✅ `openbao/scripts/init-openbao-ssh-ca.sh` | ✅ `Pytest E2E (test_02_openbao_ssh_ca.py)` |
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
| `CP-001` | Ansible Node | Configure kernel sysctl parameters for Overseer Control Plane | ✅ OK | ✅ `ansible/overseer_control_plane` | ⚡ `Integrated in Pipeline` |
| `CP-002` | Ansible Node | Configure security limits for OpenBao memlock and process limits | ✅ OK | ✅ `ansible/overseer_control_plane` | ✅ `Molecule Direct Verify` |
| `CP-003` | Ansible Node | Create Overseer control plane persistent directories | ✅ OK | ✅ `ansible/overseer_control_plane` | ✅ `Molecule Direct Verify` |
| `CP-004` | Ansible Node | Deploy Overseer systemd service unit | ✅ OK | ✅ `ansible/overseer_control_plane` | ⚡ `Integrated in Pipeline` |
| `CP-005` | Ansible Node | Enable Overseer systemd service | ✅ OK | ✅ `ansible/overseer_control_plane` | ⚡ `Integrated in Pipeline` |
| `CTRL-001` | Control Plane | PostgreSQL Database Backend Service | ✅ OK | ✅ `docker-compose.yml` | ✅ `Pytest E2E (test_01_control_plane.py)` |
| `CTRL-002` | Control Plane | Overseer Bridge Network Isolation | ✅ OK | ✅ `docker-compose.yml` | ✅ `Pytest E2E (test_01_control_plane.py)` |
| `CTRL-003` | Control Plane | Automated Full Stack Bootstrap | ✅ OK | ✅ `scripts/bootstrap.sh` | ✅ `Pytest E2E (test_01_control_plane.py)` |
| `DOC-001` | Ansible Node | Remove conflicting packages and Podman stack (RedHat/Rocky) | ✅ OK | ✅ `ansible/docker_engine` | ⚡ `Integrated in Pipeline` |
| `DOC-002` | Ansible Node | Remove conflicting packages and old Docker stack (Debian/Ubuntu) | ✅ OK | ✅ `ansible/docker_engine` | ⚡ `Integrated in Pipeline` |
| `DOC-003` | Ansible Node | Install Docker repository prerequisites (RedHat/Rocky) | ✅ OK | ✅ `ansible/docker_engine` | ⚡ `Integrated in Pipeline` |
| `DOC-004` | Ansible Node | Configure Docker CE official repository (RedHat/Rocky) | ✅ OK | ✅ `ansible/docker_engine` | ⚡ `Integrated in Pipeline` |
| `DOC-005` | Ansible Node | Install Docker repository prerequisites (Debian/Ubuntu) | ✅ OK | ✅ `ansible/docker_engine` | ⚡ `Integrated in Pipeline` |
| `DOC-006` | Ansible Node | Create keyrings directory for apt (Debian/Ubuntu) | ✅ OK | ✅ `ansible/docker_engine` | ⚡ `Integrated in Pipeline` |
| `DOC-007` | Ansible Node | Download Docker GPG key (Debian/Ubuntu) | ✅ OK | ✅ `ansible/docker_engine` | ⚡ `Integrated in Pipeline` |
| `DOC-008` | Ansible Node | Configure Docker CE repository (Debian/Ubuntu) | ✅ OK | ✅ `ansible/docker_engine` | ⚡ `Integrated in Pipeline` |
| `DOC-009` | Ansible Node | Install latest Docker CE and Compose plugin packages | ✅ OK | ✅ `ansible/docker_engine` | ⚡ `Integrated in Pipeline` |
| `DOC-010` | Ansible Node | Create /etc/docker directory | ✅ OK | ✅ `ansible/docker_engine` | ⚡ `Integrated in Pipeline` |
| `DOC-011` | Ansible Node | Deploy hardened Docker daemon configuration | ✅ OK | ✅ `ansible/docker_engine` | ✅ `Molecule Direct Verify` |
| `DOC-012` | Ansible Node | Ensure Docker and containerd services are started and enabled | ✅ OK | ✅ `ansible/docker_engine` | ⚡ `Integrated in Pipeline` |
| `DOC-013` | Ansible Node | Add admin user to docker group | ✅ OK | ✅ `ansible/docker_engine` | ⚡ `Integrated in Pipeline` |
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

---

## 2. 검증 실행 방법

```bash
# 전역 3단 정합성 자동 검증
make spec-check

# Pytest E2E 시스템 통합 테스트
make test-e2e
```
