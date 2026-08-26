# Overseer: IDC Infrastructure Provisioning & Zero-Trust Control Plane

**Overseer**는 소-중규모 IDC 온프레미스 인프라 환경의 중앙 제어 플레인(HCP Vault, HashiCorp Boundary, Prometheus)과 온프레미스 노드 프로비저닝(Ansible)을 통합 관리하는 Docker Compose 기반 오케스트레이션 툴체인입니다.

---

## 1. 주요 구성 컴포넌트

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                    Overseer Central Control Plane (Docker Compose)          │
│                                                                             │
│  ┌──────────────────┐    ┌──────────────────┐    ┌───────────────────────┐  │
│  │    HCP Vault     │    │     Boundary     │    │      Prometheus       │  │
│  │ (SSH CA, Secrets)│    │ (Zero-Trust IAM) │    │  (Metrics Monitoring) │  │
│  └────────┬─────────┘    └────────┬─────────┘    └───────────▲───────────┘  │
│           │                       │                          │              │
│  ┌────────▼───────────────────────▼──────────────────────────┴───────────┐  │
│  │                       PostgreSQL Database Backend                     │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                    Ansible Provisioning / Automation
                                       │
┌──────────────────────────────────────▼──────────────────────────────────────┐
│                            IDC On-Premise Nodes                             │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │ Roles: common (Base/sysctl/NTP) | security (Firewall/SSH Hardening)   │  │
│  │        vault_ssh_ca (Trusted CA) | boundary_target | monitoring       │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. 빠른 시작 (Quick Start)

### 1) 중앙 컨트롤 플레인 부트스트랩 (Vault + Boundary + Prometheus)

```bash
# 전체 스택 기동 및 Vault SSH CA / Boundary DB 일괄 초기화
make bootstrap
```

- **Vault Web UI**: [http://localhost:8200](http://localhost:8200)
- **Boundary Admin UI**: [http://localhost:9200](http://localhost:9200)
- **Prometheus Web UI**: [http://localhost:9090](http://localhost:9090)

### 2) 서비스 상태 점검

```bash
make status
```

### 3) 온프레미스 노드 베이스라인 프로비저닝 (Ansible)

```bash
# 사전 시뮬레이션 (Dry-Run / Diff)
make ansible-check

# 실제 프로비저닝 적용
make ansible-provision
```

### 4) Molecule 단위 테스트 & 3단 정합성 검증

```bash
# 1. 스펙 문서(docs/ansible) <-> 태스크 코드 <-> Molecule 테스트 간 3단 정합성 검증
make spec-check

# 2. Docker 기반 Rocky Linux / Ubuntu 컨테이너 단위 통합 테스트
make test
```

### 5) Full-Stack E2E 시스템 통합 테스트 (Pytest + Testinfra)

```bash
# Vault ⟷ Boundary ⟷ Ansible ⟷ Prometheus 전체 스택 E2E 테스트 실행
make test-e2e
```

---

## 3. 디렉토리 구조

```text
overseer/
├── docker-compose.yml         # [메인] Vault, Boundary, Postgres, Prometheus 일괄 기동
├── .env.example               # 환경 변수 템플릿
├── Makefile                   # 원클릭 통합 제어 명령어 모음
├── AGENTS.md                  # 프로젝트 컨텍스트 및 AI 협업 가이드
├── README.md                  # 본 문서
│
├── tests/                     # 🧪 [E2E 시스템 통합 테스트 스위트 (Pytest + Testinfra)]
│   ├── conftest.py            # 공통 픽스처 (API 세션, URL, 토큰)
│   ├── test_01_control_plane.py # Postgres, Vault, Boundary, Prometheus 헬스 검증
│   ├── test_02_vault_ssh_ca.py  # Vault SSH CA 공개키 생성 및 인증서 서명 검증
│   ├── test_03_boundary.py      # Boundary Controller/Worker 프록시 검증
│   └── test_04_ansible_e2e.py   # Ansible 인벤토리 & Prometheus 스크랩 타겟 연동 검증
│
├── docs/                      # [전역 운영 문서]
│   ├── control-plane/         # 🔐 [중앙 컨트롤 플레인 스펙]
│   │   ├── INDEX.md
│   │   └── overview.md        # CTRL-001~003, VAULT/BND/PROM-CTRL
│   ├── ansible/               # 📑 [Role별 태스크 스펙 및 3단 추적 매트릭스]
│   │   ├── INDEX.md           # 전체 태스크 카탈로그 및 3-Way Traceability Matrix
│   │   ├── common.md          # COMMON-001 ~ COMMON-015
│   │   ├── security.md        # SEC-001 ~ SEC-010
│   │   ├── vault_ssh_ca.md    # VAULT-001 ~ VAULT-007
│   │   ├── boundary_target.md # BND-001 ~ BND-003
│   │   └── monitoring.md      # MON-001 ~ MON-005
│   ├── tests/                 # 🧪 [테스트 및 검증 세분화 문서]
│   │   ├── INDEX.md           # 테스트 종합 개요 및 네비게이션
│   │   ├── TRACEABILITY_MATRIX.md # 3단 정합성 검증 매트릭스 리포트 (자동 생성)
│   │   ├── E2E_TESTING_GUIDELINE.md # Pytest + Testinfra 시스템 통합 테스트 가이드
│   │   └── ANSIBLE_TESTING_GUIDELINE.md # 4단계 테스팅 & Molecule 멱등성 검증 가이드
│   └── PROVISIONING_AND_MIGRATION_GUIDELINE.md # 온프레미스 프로비저닝 & 마이그레이션 가이드
│
├── vault/                     # Vault 서버 설정 및 SSH CA 자동화 스크립트
├── boundary/                  # Boundary Controller/Worker 설정 및 DB 스크립트
├── prometheus/                # 메트릭 스크랩 설정
├── scripts/                   # 부트스트랩, 헬스체크 및 3단 검증 스크립트
└── ansible/                   # 온프레미스 노드 프로비저닝 레이어 (Roles, Playbooks, Molecule)
```

---

## 4. 상세 문서 링크

- 🧪 [3-Way Traceability 매트릭스 리포트](file:///home/ppzxc/projects/overseer/docs/tests/TRACEABILITY_MATRIX.md)
- 🧪 [테스트 프레임워크 종합 가이드 (`docs/tests/`)](file:///home/ppzxc/projects/overseer/docs/tests/INDEX.md)
- 📑 [Ansible 태스크 스펙 매트릭스 (`docs/ansible/`)](file:///home/ppzxc/projects/overseer/docs/ansible/INDEX.md)
- 🔐 [컨트롤 플레인 스펙 (`docs/control-plane/`)](file:///home/ppzxc/projects/overseer/docs/control-plane/INDEX.md)
- 📖 [온프레미스 프로비저닝 및 마이그레이션 가이드라인](file:///home/ppzxc/projects/overseer/docs/PROVISIONING_AND_MIGRATION_GUIDELINE.md)
- ⚙️ [Ansible 세부 사용법 및 인벤토리 가이드](file:///home/ppzxc/projects/overseer/ansible/README.md)


