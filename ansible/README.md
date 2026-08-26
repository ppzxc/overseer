# Overseer Ansible Provisioning & Automation

**Overseer Ansible**은 소-중규모 IDC 온프레미스 인프라 환경의 서버 베이스라인 프로비저닝, HCP Vault SSH CA 연동, HashiCorp Boundary Target 구성, 보안 하드닝 및 모니터링 에이전트 구성을 자동화하는 툴체인입니다.

---

## 1. 디렉토리 및 파일 구성

```
ansible/
├── ansible.cfg                    # Ansible 기본 설정 (인벤토리 경로, SSH 파이프라이닝 등)
├── Dockerfile                     # 컨테이너화된 Ansible 및 Molecule 실행 환경 이미지 정의
├── docker-compose.yml             # Docker Compose 기반 실행 설정
├── docker-run.sh                  # Docker 컨테이너 실행 래퍼 스크립트
├── README.md                      # 본 문서 (구현 내용 및 운영 가이드)
├── inventory/
│   ├── hosts.yml                  # IDC 노드 인벤토리 정의 (compute, storage, gateway)
│   └── group_vars/
│       ├── all.yml                # 전역 변수 (타임존, 관리자 계정, SSH 공개키 등)
│       └── idc_servers.yml        # IDC 서버 공통 변수 (NTP, sysctl, 기본 패키지 등)
├── molecule/
│   └── default/                   # Molecule 기본 통합 테스트 시나리오
│       ├── molecule.yml           # Molecule Docker 플랫폼 정의 (Rocky, Ubuntu)
│       ├── converge.yml           # 테스트 대상 Role 실행 플레이북
│       └── verify.yml             # 상태 단언(Assert) 검증 플레이북
├── playbooks/
│   ├── site.yml                   # 전체 인프라 일괄 적용 메인 엔트리포인트
│   ├── provision.yml              # 신규 서버 베이스라인 프로비저닝 플레이북
│   └── maintenance.yml            # 롤링 업데이트 기반 보안 패치 및 유지보수 플레이북
└── roles/
    ├── common/                    # 기본 패키지, Chrony NTP, sysctl 커널 튜닝, 관리자 계정(sudoers)
    ├── security/                  # SSH 하드닝, 방화벽(UFW/Firewalld), Fail2ban
    ├── vault_ssh_ca/              # HCP Vault SSH CA 공개키 등록 및 TrustedUserCAKeys 설정
    ├── boundary_target/           # Boundary Target 메타데이터 생성 및 원격 접근 환경 구성
    └── monitoring/                # Prometheus Node Exporter 바이너리 배포 및 Systemd 등록
```

---

## 2. 구현된 역할(Roles) 상세

### 1) `common`
- **타임존 설정**: `Asia/Seoul` (기본값)
- **NTP 동기화**: `chrony` 패키지 설치 및 IDC 권장 타임 서버 구성 (`chrony.conf.j2`)
- **필수 유틸리티 패키지 일괄 설치**: `curl`, `wget`, `git`, `vim`, `htop`, `iotop`, `net-tools`, `jq` 등
- **커널 튜닝 (sysctl)**: 파일 디스크립터(`fs.file-max`), 소켓 버퍼(`net.core.somaxconn`), `vm.swappiness=10`, `vm.max_map_count=262144` 최적화
- **시스템 한도 & 저널링**: 보안 리소스 제한(`/etc/security/limits.d/99-limits.conf`, nofile/nproc 65535), `systemd-journald` 2GB 보존 상한 설정
- **관리자 계정 및 SSH 키 구성**: 지정된 관리자 계정(`infra-admin`) 생성, 무비밀번호 sudo 권한 부여, `admin_ssh_public_keys` 등록

### 2) `security`
- **SSH 보안 하드닝**:
  - 커스텀 SSH 포트(`ssh_port`) 지정 지원
  - `PermitRootLogin prohibit-password` (기본값: 공개키/인증서 기반 루트 접근 허용, 추후 no로 전환 가능)
  - `PasswordAuthentication yes/no` (초기 배포 시 yes, SSH 키 검증 완료 후 no 전환 권장)
  - `MaxAuthTries 3`, 유휴 세션 타임아웃 구성
- **호스트 방화벽 & 서브넷 격리**:
  - Debian/Ubuntu: `ufw` 활성화 (기본 인바운드 차단, 관리망/모니터링망 서브넷 화이트리스트 적용)
  - RedHat/Rocky: `firewalld` 활성화 및 Rich Rule 기반 서브넷 허용
- **SELinux 제어**: `permissive` 모드로 설정하여 기존 서비스 영향 없이 감사 로그 수집
- **감사 및 모니터링 (Auditd)**: `/etc/passwd`, `/etc/shadow`, `/etc/sudoers`, `sshd_config` 파일 수정 감시 및 execve 로깅
- **침입 방지 & Sudo 정책**: `fail2ban` SSH jail 활성화, `timestamp_timeout=15` 및 `/var/log/sudo.log` 독립 로깅

### 3) `vault_ssh_ca` (선택적 / Feature Toggle 지원)
- `enable_vault_ssh_ca: false`일 경우 자동으로 스킵되므로 Vault/OpenBao 미도입 환경에서도 안전하게 실행 가능
- **HCP Vault / OpenBao SSH CA 연동 활성화 시**:
  - `/etc/ssh/trusted-user-ca-keys.pem`에 Vault/OpenBao SSH CA 공개키 배포
  - `sshd_config`에 `TrustedUserCAKeys` 및 `AuthorizedPrincipalsFile` 설정
  - 엔지니어가 발급받은 단기 SSH Certificate로 안전하게 온프레미스 노드에 인증 및 접속 가능

### 4) `boundary_target` (선택적 / Feature Toggle 지원)
- `enable_boundary: false`일 경우 자동으로 스킵됩니다.
- **HashiCorp Boundary 연동 준비**:
  - 타겟 노드 메타데이터(`/etc/boundary/node-metadata.json`) 기록 (호스트명, IP, 타겟 유형, 태그)
  - 사내망을 외부에 직접 노출하지 않고 Boundary Worker를 통한 제로 트러스트 터널링 접속 지원

### 5) `monitoring` (하이브리드 관제 & OpenObserve)
- **Prometheus Node Exporter**:
  - 아키텍처(amd64 / arm64) 자동 판별 후 GitHub 릴리즈 바이너리 다운로드
  - 전용 시스템 계정(`node_exporter`) 생성 및 Systemd 서비스 등록 (`:9100`)
- **OpenTelemetry Collector Contrib (`otelcol-contrib`)**:
  - Standalone Systemd 데몬 배포
  - 로컬 Node Exporter 스크랩(`127.0.0.1:9100`) + OS/Audit 시스템 로그(`/var/log/*`, `/var/log/audit`) 수집
  - 어플리케이션 OTLP gRPC(`:4317`) / HTTP(`:4318`) 수신 및 중앙 **OpenObserve**로 단일 OTLP 스트리밍 전송


---

## 3. 지원 OS 및 환경

- **RHEL 계열 전 세대 지원**:
  - **CentOS 6** (레거시): EOL vault repo 자동 전환, iptables 방화벽, ntpd 동기화 (OpenSSH 5.3 한계로 Vault CA 제외)
  - **CentOS 7** (EOL): EOL vault repo 전환, firewalld, chrony, Vault SSH CA 지원
  - **CentOS 8 / Stream**: dnf, firewalld, chrony, Vault SSH CA 지원
  - **Rocky Linux 9 / 10** (최신): dnf, firewalld, chrony, Vault SSH CA 및 Boundary 완벽 호환
- **Debian / Ubuntu 계열**: Ubuntu 20.04/22.04/24.04, Debian 11/12 (apt, ufw, chrony)
- **Ansible 버전**: Ansible 2.14 이상


---

## 4. 플레이북 실행 및 호스트 선택 가이드

Ansible의 `--limit` (`-l`) 옵션과 인벤토리 그룹을 통해 **원하는 특정 단일 호스트, 복수 호스트, OS 세대별 그룹**만 정밀하게 선택하여 실행할 수 있습니다.

### 1) 호스트 선택 실행 패턴

```bash
# ① 특정 단일 호스트만 실행
ansible-playbook -i inventory/hosts.yml playbooks/provision.yml --limit storage-01.idc.internal

# ② 복수 호스트 지정 실행 (쉼표 구분)
ansible-playbook -i inventory/hosts.yml playbooks/provision.yml --limit "node-01.idc.internal,node-02.idc.internal"

# ③ OS 세대별 그룹만 선택 실행 (예: CentOS 6 또는 Rocky Linux 그룹만)
ansible-playbook -i inventory/hosts.yml playbooks/provision.yml --limit legacy_el6_nodes
ansible-playbook -i inventory/hosts.yml playbooks/provision.yml --limit modern_rocky_nodes

# ④ 역할별 그룹만 선택 실행
ansible-playbook -i inventory/hosts.yml playbooks/provision.yml --limit compute_nodes
ansible-playbook -i inventory/hosts.yml playbooks/provision.yml --limit storage_nodes

# ⑤ 와일드카드 패턴 매칭
ansible-playbook -i inventory/hosts.yml playbooks/provision.yml --limit "node-*.idc.internal"

# ⑥ 특정 호스트 제외 실행 (compute 그룹 중 node-02 제외)
ansible-playbook -i inventory/hosts.yml playbooks/provision.yml --limit "compute_nodes:!node-02.idc.internal"
```

### 2) 태그(Tag) 및 사전 시뮬레이션 조합
```bash
# 특정 호스트에 대해 Dry-Run (Check Mode) 시뮬레이션
ansible-playbook -i inventory/hosts.yml playbooks/provision.yml --limit storage-01.idc.internal --check --diff

# 특정 호스트에 특정 역할 태그만 적용
ansible-playbook -i inventory/hosts.yml playbooks/provision.yml --limit storage-01.idc.internal --tags "monitoring"
```

### 3) 호스트별 개별 설정 분리 (`host_vars/`)
- 특정 호스트 전용 방화벽 오픈 포트, 고유 sysctl 값, IP 오버라이드는 `inventory/host_vars/<hostname>.yml` 파일에 독립적으로 정의하여 관리합니다.
  - 예: `inventory/host_vars/storage-01.idc.internal.yml` (NFS/iSCSI 포트 및 I/O sysctl 개별 지정)

---

## 5. Docker 컨테이너 기반 실행 가이드

로컬 머신에 Python이나 Ansible 환경을 직접 설치하지 않고 격리된 Docker 환경에서 플레이북을 실행할 수 있습니다.

### 1) 래퍼 스크립트(`docker-run.sh`) 사용 (가장 간편)

스크립트 실행 시 필요한 Docker 이미지가 자동으로 빌드되며, 호스트의 `~/.ssh` 키 및 SSH Agent 소켓(`$SSH_AUTH_SOCK`), Vault 환경 변수가 자동 전달됩니다.

```bash
# ① 기본 도움말 확인
./docker-run.sh

# ② 신규 서버 프로비저닝 실행
./docker-run.sh playbooks/provision.yml

# ③ 특정 호스트 대상 Dry-Run 시뮬레이션
./docker-run.sh playbooks/provision.yml --limit storage-01.idc.internal --check --diff

# ④ Ansible ad-hoc 명령어 또는 린트 실행
./docker-run.sh ansible all -i inventory/hosts.yml -m ping
./docker-run.sh ansible-lint

# ⑤ Molecule 통합 테스트 실행 (Rocky Linux & Ubuntu 컨테이너 테스트)
./docker-run.sh molecule test
```

### 2) Docker Compose 사용

```bash
# 이미지 빌드
docker compose build

# 플레이북 실행
docker compose run --rm ansible playbooks/provision.yml --limit compute_nodes
```

### 3) Docker 직접 실행 (수동)

```bash
# 이미지 빌드
docker build -t overseer-ansible .

# 실행 (SSH 키 및 프로젝트 마운트)
docker run --rm -it \
  -v "$(pwd):/ansible" \
  -v "${HOME}/.ssh:/root/.ssh:ro" \
  -w /ansible \
  overseer-ansible playbooks/provision.yml --limit storage-01.idc.internal
```

---

## 6. 온프레미스 신규 프로비저닝 vs 기존 머신 마이그레이션 가이드라인

상세 가이드라인 전문은 [../docs/PROVISIONING_AND_MIGRATION_GUIDELINE.md](file:///home/ppzxc/projects/overseer/docs/PROVISIONING_AND_MIGRATION_GUIDELINE.md)를 참고하십시오.


### 핵심 요약

| 역할 (Role) | 신규 서버 프로비저닝 (Greenfield) | 기존 머신 마이그레이션 (Brownfield) 주의사항 |
|---|---|---|
| **`common`** | 타임존/NTP, 기본 도구, sysctl 튜닝 일괄 적용 | 기존 NTP 데몬 충돌 점검, 기존 앱 전용 sysctl 보존, 기존 계정 덮어쓰기 방지 |
| **`security`** | SSH 하드닝 및 방화벽 기본 차단 즉시 적용 | **SSH 락아웃 방지** (Vault CA 인증 성공 전 비밀번호 차단 금지), **운영 포트 사전 조사** 후 방화벽 적용 |
| **`monitoring`** | Node Exporter 즉시 배포 (포트 9100) | 기존 모니터링 데몬 포트 중복 확인, 프로메테우스 수집기 방화벽 허용 |

#### 안전한 마이그레이션 절차:
1. `ss -tulpn` 등으로 기존 LISTEN 포트 수집 후 `inventory/host_vars/<hostname>.yml`에 등록
2. `--check --diff`로 Dry-Run 시뮬레이션
3. `--tags "common,monitoring,vault"` 적용 후 별도 터미널에서 Vault SSH 키 접속 검증
4. 정상 확인 후 `--tags "security,boundary"`로 방화벽 및 SSH 하드닝 적용

---

## 7. 인프라 운영 및 문서화 규칙

- **문서 동기화**: 신규 역할 추가, 변수 변경, 플레이북 수정 등 인프라 형상에 변경 사항이 발생할 경우 **반드시 본 `README.md`를 함께 업데이트**해야 합니다.
- **멱등성 검증**: 모든 신규 태스크는 2회 이상 연속 실행 시 변경(`changed=0`)이 없도록 멱등성을 검증해야 합니다.

