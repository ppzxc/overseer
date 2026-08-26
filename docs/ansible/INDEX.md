# Ansible Roles Task Specification & 3-Way Traceability Matrix

본 문서는 **Overseer**의 Ansible 역할(Role)별 실행 태스크 목록, 고유 Spec ID, 그리고 **문서(Spec) ⟷ 코드(Tasks) ⟷ Molecule 테스트(Verification)** 간의 **3단 추적 매트릭스 (3-Way Traceability Matrix)**를 정의합니다.

---

## 1. 역할별 상세 스펙 문서

- 📄 [Common Role 스펙 (`docs/ansible/common.md`)](file:///home/ppzxc/projects/overseer/docs/ansible/common.md): 타임존, 패키지, Chrony NTP, 커널(sysctl) 튜닝, 관리자 계정 (`COMMON-001` ~ `COMMON-015`)
- 📄 [Security Role 스펙 (`docs/ansible/security.md`)](file:///home/ppzxc/projects/overseer/docs/ansible/security.md): SSH 하드닝, UFW/Firewalld/iptables 방화벽, Fail2ban (`SEC-001` ~ `SEC-010`)
- 📄 [Vault SSH CA Role 스펙 (`docs/ansible/vault_ssh_ca.md`)](file:///home/ppzxc/projects/overseer/docs/ansible/vault_ssh_ca.md): Vault SSH CA 공개키 등록 및 TrustedUserCAKeys (`VAULT-001` ~ `VAULT-007`)
- 📄 [Boundary Target Role 스펙 (`docs/ansible/boundary_target.md`)](file:///home/ppzxc/projects/overseer/docs/ansible/boundary_target.md): Boundary Target 메타데이터 구성 (`BND-001` ~ `BND-003`)
- 📄 [Monitoring Role 스펙 (`docs/ansible/monitoring.md`)](file:///home/ppzxc/projects/overseer/docs/ansible/monitoring.md): Prometheus Node Exporter 배포 및 서비스 등록 (`MON-001` ~ `MON-005`)

---

## 2. 3단 검증 매트릭스 (3-Way Traceability Matrix)

| Spec ID | 역할 (Role) | 태스크 명칭 (Task Name) | 코드 구현 (`roles/*/tasks/main.yml`) | Molecule 검증 (`molecule/default/verify.yml`) |
|---|---|---|:---:|:---:|
| `COMMON-001` | `common` | `Set timezone` | ✅ 구현 | `[VERIFY-COMMON-001]` |
| `COMMON-002` | `common` | `Fix EOL CentOS 6 / 7 Vault Repositories` | ✅ 구현 | 조건부 (CentOS 6/7) |
| `COMMON-003` | `common` | `Install common packages (Debian/Ubuntu)` | ✅ 구현 | ✅ 통합 검증 |
| `COMMON-004` | `common` | `Install EPEL repository (RedHat/CentOS 7, Rocky 8, 9)` | ✅ 구현 | ✅ 통합 검증 |
| `COMMON-005` | `common` | `Install common packages (RedHat/CentOS 6, 7 via YUM)` | ✅ 구현 | ✅ 통합 검증 |
| `COMMON-006` | `common` | `Install common packages (RHEL/Rocky 8, 9, 10 via DNF)` | ✅ 구현 | ✅ 통합 검증 |
| `COMMON-007` | `common` | `Install optional diagnostic tools (htop, iotop)` | ✅ 구현 | ✅ 통합 검증 |
| `COMMON-008` | `common` | `Configure Chrony NTP servers (Modern OS)` | ✅ 구현 | `[VERIFY-COMMON-008]` |
| `COMMON-009` | `common` | `Ensure Chrony service is running (Modern OS)` | ✅ 구현 | `[VERIFY-COMMON-008]` |
| `COMMON-010` | `common` | `Ensure NTP service is running (CentOS 6 legacy)` | ✅ 구현 | 조건부 (CentOS 6) |
| `COMMON-011` | `common` | `Apply sysctl kernel tuning` | ✅ 구현 | `[VERIFY-COMMON-011]` |
| `COMMON-012` | `common` | `Ensure admin user group exists` | ✅ 구현 | `[VERIFY-COMMON-012]` |
| `COMMON-013` | `common` | `Ensure admin user exists with sudo privileges` | ✅ 구현 | `[VERIFY-COMMON-013]` |
| `COMMON-014` | `common` | `Enable passwordless sudo for admin user` | ✅ 구현 | `[VERIFY-COMMON-014]` |
| `COMMON-015` | `common` | `Deploy admin SSH public keys` | ✅ 구현 | `[VERIFY-COMMON-015]` |
| `SEC-001` | `security` | `Configure SSH Hardening parameters` | ✅ 구현 | `[VERIFY-SEC-001]` |
| `SEC-002` | `security` | `Ensure UFW is installed (Debian)` | ✅ 구현 | ✅ 통합 검증 |
| `SEC-003` | `security` | `Allow incoming TCP ports via UFW (Debian)` | ✅ 구현 | ✅ 통합 검증 |
| `SEC-004` | `security` | `Enable UFW with default deny incoming (Debian)` | ✅ 구현 | ✅ 통합 검증 |
| `SEC-005` | `security` | `Ensure firewalld is installed and running (RHEL/Rocky 7+)` | ✅ 구현 | ✅ 통합 검증 |
| `SEC-006` | `security` | `Ensure firewalld service is started and enabled (RHEL/Rocky 7+)` | ✅ 구현 | ✅ 통합 검증 |
| `SEC-007` | `security` | `Allow incoming TCP ports via firewalld (RHEL/Rocky 7+)` | ✅ 구현 | ✅ 통합 검증 |
| `SEC-008` | `security` | `Allow incoming TCP ports via iptables (CentOS 6)` | ✅ 구현 | 조건부 (CentOS 6) |
| `SEC-009` | `security` | `Install fail2ban package if available` | ✅ 구현 | ✅ 통합 검증 |
| `SEC-010` | `security` | `Ensure fail2ban is running and enabled (if installed)` | ✅ 구현 | ✅ 통합 검증 |
| `VAULT-001` | `vault_ssh_ca` | `Skip Vault SSH CA if disabled or key is empty` | ✅ 구현 | `[VERIFY-VAULT-001]` |
| `VAULT-002` | `vault_ssh_ca` | `Check OpenSSH CA capability (requires OpenSSH >= 5.4, RHEL/CentOS 7+)` | ✅ 구현 | 조건부 (CentOS 6) |
| `VAULT-003` | `vault_ssh_ca` | `Ensure SSH configuration directory exists` | ✅ 구현 | ✅ 통합 검증 |
| `VAULT-004` | `vault_ssh_ca` | `Deploy Vault SSH CA Public Key` | ✅ 구현 | ✅ 통합 검증 |
| `VAULT-005` | `vault_ssh_ca` | `Ensure AuthorizedPrincipals directory exists` | ✅ 구현 | ✅ 통합 검증 |
| `VAULT-006` | `vault_ssh_ca` | `Create admin user principals file` | ✅ 구현 | ✅ 통합 검증 |
| `VAULT-007` | `vault_ssh_ca` | `Configure sshd to trust Vault CA Keys and AuthorizedPrincipals` | ✅ 구현 | ✅ 통합 검증 |
| `BND-001` | `boundary_target` | `Skip Boundary Target if disabled` | ✅ 구현 | `[VERIFY-BND-001]` |
| `BND-002` | `boundary_target` | `Create Boundary target metadata directory` | ✅ 구현 | ✅ 통합 검증 |
| `BND-003` | `boundary_target` | `Write Boundary Target Node Info` | ✅ 구현 | ✅ 통합 검증 |
| `MON-001` | `monitoring` | `Create node_exporter system group` | ✅ 구현 | `[VERIFY-MON-001]` |
| `MON-002` | `monitoring` | `Create node_exporter system user` | ✅ 구현 | `[VERIFY-MON-002]` |
| `MON-003` | `monitoring` | `Download and install Node Exporter binary` | ✅ 구현 | `[VERIFY-MON-003]` |
| `MON-004` | `monitoring` | `Create systemd service for node_exporter` | ✅ 구현 | `[VERIFY-MON-004]` |
| `MON-005` | `monitoring` | `Ensure node_exporter service is started and enabled` | ✅ 구현 | `[VERIFY-MON-005]` |

---

## 3. 자동 3단 검증 실행 (Automated Verification)

```bash
# 코드, 스펙 문서, Molecule 테스트 간 3단 정합성 검증
make spec-check
```
