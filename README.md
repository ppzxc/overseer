# Overseer: IDC Infrastructure Provisioning & Zero-Trust Control Plane

**Overseer**는 소-중규모 IDC 온프레미스 인프라 환경의 중앙 제어 플레인(OpenBao, HashiCorp Boundary, PostgreSQL)과 온프레미스 노드 프로비저닝(Ansible)을 통합 관리하는 Docker Compose 기반 오케스트레이션 툴체인입니다.

---

## 1. 주요 구성 컴포넌트

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                    Overseer Central Control Plane (Docker Compose)          │
│                                                                             │
│  ┌──────────────────┐    ┌──────────────────┐    ┌───────────────────────┐  │
│  │     OpenBao      │    │     Boundary     │    │ Semaphore UI (Web UI) │  │
│  │ (SSH CA, Secrets)│    │ (Zero-Trust IAM) │    │ & Ansible Runner      │  │
│  └────────┬─────────┘    └────────┬─────────┘    └───────────▲───────────┘  │
│           │                       │                          │              │
│  ┌────────▼───────────────────────▼──────────────────────────┴───────────┐  │
│  │                       PostgreSQL Database Backend                     │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                    Ansible Provisioning / Automation (Web UI & CLI)
                                       │
┌──────────────────────────────────────▼──────────────────────────────────────┐
│                            IDC On-Premise Nodes                             │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │ Roles: common (Base/sysctl/NTP) | security (Firewall/SSH Hardening)   │  │
│  │        docker_engine (Docker CE / Hardening)                          │  │
│  │        overseer_control_plane (Memlock / Sysctl / Systemd unit)       │  │
│  │        openbao_ssh_ca (Trusted CA) | boundary_target | monitoring     │  │
│  │        (OTel Hostmetrics + Docker Metrics + OS Audit Logs Pipeline)   │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘

```

---

## 2. 인벤토리 그룹 분리 구조 (`overseer` vs `servers`)

| 인벤토리 그룹 | 대상 역할 | 주요 배포 Playbook & Roles |
|---|---|---|
| **`overseer`** | Overseer 컨트롤 플레인이 구동되는 호스트 서버 | `provision_overseer.yml` (`common`, `security`, `docker_engine`, `overseer_control_plane`, `monitoring`) |
| **`servers`** | 일반 온프레미스 타겟 서버 노드 | `provision_servers.yml` (`common`, `security`, `openbao_ssh_ca`, `boundary_target`, `monitoring`) |

---

## 3. 빠른 시작 (Quick Start)

### 0) 로컬 환경 설정 및 인벤토리 준비 (Git 분리 및 격리)
실서버 IP, SSH 포트, 시크릿 정보는 Git에 커밋되지 않고 `.gitignore`로 격리됩니다.
```bash
# 1. 컨트롤 플레인 환경변수 템플릿 복사 및 설정
cp .env.example .env

# 2. Ansible 인벤토리 템플릿 복사 및 실서버 정보 입력
cp ansible/inventory/hosts.yml.example ansible/inventory/hosts.yml
```

### 1) Overseer 컨트롤 플레인 호스트 프로비저닝 (Docker CE + Podman 제거 + 하드닝)
```bash
make ansible-provision-overseer
```

### 2) 중앙 컨트롤 플레인 부트스트랩 (OpenBao + Boundary + Semaphore + Postgres)
```bash
# 전체 스택 기동 및 OpenBao SSH CA / Boundary DB / Semaphore DB 일괄 초기화
make bootstrap
```

- **OpenBao Web UI**: [http://localhost:8200](http://localhost:8200)
- **Boundary Admin UI**: [http://localhost:9200](http://localhost:9200)
- **Semaphore Ansible Web UI**: [http://localhost:3000](http://localhost:3000) (초기 계정: `admin` / `semaphoreadmin`)

### 3) 온프레미스 대상 서버 프로비저닝 (Semaphore Web UI 또는 CLI)
- **Web UI 방식**: [http://localhost:3000](http://localhost:3000) 접속 후 Semaphore Task 템플릿에서 `Provision Servers` 실행
- **CLI 방식**:
```bash
# 대상 서버 베이스라인 프로비저닝 (OpenBao SSH CA + Boundary Target + OTEL Agent)
make ansible-provision-servers

# 전체(overseer + servers) 일괄 프로비저닝
make ansible-provision
```

### 4) 통합 테스트 실행
```bash
# 1. 3단 정합성 검증 (스펙 문서 <-> 코드 <-> 테스트)
make spec-check

# 2. Docker 기반 Rocky Linux / Ubuntu 컨테이너 단위 통합 테스트 (Molecule)
make test-molecule

# 3. E2E 시스템 통합 테스트 실행 (Pytest)
make test-e2e
```

---

## 4. 디렉토리 구조

```text
overseer/
├── docker-compose.yml         # [메인] OpenBao, Boundary, Postgres 일괄 기동
├── .env.example               # 환경 변수 템플릿
├── Makefile                   # 원클릭 통합 제어 명령어 모음
├── AGENTS.md                  # 프로젝트 컨텍스트 및 AI 협업 가이드
├── README.md                  # 본 문서
│
├── tests/                     # 🧪 [E2E 시스템 통합 테스트 스위트 (Pytest + Testinfra)]
│   ├── conftest.py            # 공통 픽스처 (API 세션, URL, 토큰)
│   ├── test_00_spec_traceability.py # 3단 정합성 검증 테스트
│   ├── test_01_control_plane.py # Postgres, OpenBao, Boundary 헬스 검증
│   ├── test_02_openbao_ssh_ca.py # OpenBao SSH CA 공개키 생성 및 인증서 서명 검증
│   ├── test_03_boundary.py      # Boundary Controller/Worker 프록시 검증
│   └── test_04_ansible_e2e.py   # Ansible 인벤토리(overseer/servers) 및 플레이북 아키텍처 검증
│
├── docs/                      # [전역 운영 문서]
│   ├── control-plane/         # 🔐 [중앙 컨트롤 플레인 스펙]
│   ├── ansible/               # 📑 [Role별 태스크 스펙 및 3단 추적 매트릭스]
│   │   ├── docker_engine.md   # DOC-001 ~ DOC-013 (Docker CE / Podman 제거)
│   │   ├── overseer_control_plane.md # CP-001 ~ CP-005 (호스트 커널/Systemd)
│   │   ├── common.md          # COMMON-001 ~ COMMON-017
│   │   ├── security.md        # SEC-001 ~ SEC-015
│   │   ├── openbao_ssh_ca.md  # BAO-001 ~ BAO-007
│   │   ├── boundary_target.md # BND-001 ~ BND-003
│   │   └── monitoring.md      # MON-001 ~ MON-011 (OTEL Col + Docker Metrics)
│   └── tests/                 # 🧪 [테스트 및 검증 세분화 문서]
│
├── openbao/                   # OpenBao 서버 설정 및 SSH CA 자동화 스크립트
├── boundary/                  # Boundary Controller/Worker 설정 및 DB 스크립트
├── scripts/                   # 부트스트랩, 헬스체크 및 3단 검증 스크립트
└── ansible/                   # 온프레미스 노드 프로비저닝 레이어 (Roles, Playbooks, Molecule)
```

---

## 5. 상세 문서 링크

- 🧪 [3-Way Traceability 매트릭스 리포트](file:///home/ppzxc/projects/overseer/docs/tests/TRACEABILITY_MATRIX.md)
- 📑 [Ansible 태스크 스펙 매트릭스 (`docs/ansible/`)](file:///home/ppzxc/projects/overseer/docs/ansible/INDEX.md)
- 🔐 [컨트롤 플레인 스펙 (`docs/control-plane/`)](file:///home/ppzxc/projects/overseer/docs/control-plane/INDEX.md)
- ⚙️ [Ansible 세부 사용법 및 인벤토리 가이드](file:///home/ppzxc/projects/overseer/ansible/README.md)
