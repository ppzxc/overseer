# Overseer: IDC Infrastructure Zero-Trust Control Plane

**Overseer**는 소-중규모 IDC 온프레미스 인프라 환경의 중앙 제어 플레인(OpenBao, HashiCorp Boundary, Semaphore UI, PostgreSQL)을 일괄 오케스트레이션하고, 독립된 Ansible GitOps 저장소(`node-provisioner`)를 통해 온프레미스 노드 프로비저닝을 제어하는 Docker Compose 기반 중앙 컨트롤 플레인입니다.

---

## 1. 주요 구성 컴포넌트

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                    Overseer Central Control Plane (Docker Compose)          │
│                                                                             │
│  ┌──────────────────┐    ┌──────────────────┐    ┌───────────────────────┐  │
│  │     OpenBao      │    │     Boundary     │    │ Semaphore UI (Web UI) │  │
│  │ (SSH CA, Secrets)│    │ (Zero-Trust IAM) │    │ & GitOps Orchestrator │  │
│  │  [Raft Storage]  │    └────────┬─────────┘    └───────────▲───────────┘  │
│  └──────────────────┘             │                          │              │
│                          ┌────────▼──────────────────────────┴───────────┐  │
│                          │     PostgreSQL (Boundary & Semaphore DB)      │  │
│                          └───────────────────────────────────────────────┘  │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                    GitOps Pull & SSH Orchestration
                                       │
┌──────────────────────────────────────▼──────────────────────────────────────┐
│                            IDC On-Premise Nodes                             │
│     Target Servers bootstrapped via 'node-provisioner' Ansible Roles        │
└─────────────────────────────────────────────────────────────────────────────┘

```

---

## 2. 빠른 시작 (Quick Start)

### 0) 로컬 환경 설정 (Git 분리 및 격리)
시크릿 및 설정 정보는 Git에 커밋되지 않고 `.gitignore`로 격리됩니다.
```bash
# 컨트롤 플레인 환경변수 템플릿 복사 및 설정
cp .env.example .env
```

### 1) 중앙 컨트롤 플레인 부트스트랩 및 서비스 제어
```bash
# [전체 통합] 전체 스택 기동 및 초기화 (OpenBao SSH CA / Boundary DB / Semaphore DB & GitOps 시딩)
make bootstrap        # 또는 make up

# [전체 상태 확인 / 중지]
make status           # PostgreSQL, OpenBao, Boundary, Semaphore 헬스체크
make down             # 전체 서비스 중지

# [개별 서비스 기동/중지/초기화]
make start-openbao    # OpenBao만 기동 및 SSH CA 언실/초기화
make start-boundary   # Boundary만 기동 및 DB 마이그레이션
make start-semaphore  # Semaphore만 기동 및 GitOps 템플릿 시딩
make stop-boundary    # Boundary 컨테이너 중지
```

- **OpenBao Web UI**: [http://localhost:8200](http://localhost:8200)
- **Boundary Admin UI**: [http://localhost:9200](http://localhost:9200)
- **Semaphore Ansible Web UI**: [http://localhost:3000](http://localhost:3000) (초기 계정: `admin` / `semaphoreadmin`)

### 2) 온프레미스 대상 서버 프로비저닝 실행
- **Semaphore Web UI 접속**: [http://localhost:3000](http://localhost:3000)
- 사전 등록된 Task 템플릿(`Provision Target Servers`, `Regular Maintenance` 등)에서 **`[Run]`** 버튼 클릭만으로 즉시 프로비저닝 실행 (원격 GitHub `node-provisioner` 자동 연동)

### 3) 3단 정합성 검증 및 E2E 테스트
```bash
# 1. 3단 정합성 검증 (스펙 문서 <-> 코드 <-> 테스트)
make spec-check

# 2. Control Plane E2E 시스템 통합 테스트 실행 (Pytest)
make test-e2e
```

---

## 3. 디렉토리 구조

```text
overseer/
├── AGENTS.md                  # AI 및 엔지니어 협업 가이드
├── CONTEXT.md                 # Overseer 도메인 컨텍스트
├── README.md                  # 본 문서
├── docker-compose.yml         # OpenBao, Boundary, Semaphore, Postgres 일괄 기동
├── .env.example               # 환경 변수 템플릿
├── Makefile                   # 원클릭 통합 제어 인터페이스 (make bootstrap, status 등)
│
├── docs/                      # [전역 문서 저장소]
│   ├── control-plane/         # [중앙 컨트롤 플레인 스펙 및 태스크 매트릭스]
│   ├── tests/                 # [테스트 및 검증 가이드라인]
│   └── adr/                   # Architecture Decision Records
│
├── tests/                     # [E2E 시스템 통합 테스트 스위트 (Pytest)]
│   ├── conftest.py
│   ├── test_00_spec_traceability.py
│   ├── test_01_control_plane.py
│   ├── test_02_openbao_ssh_ca.py
│   ├── test_03_boundary.py
│   ├── test_04_ansible_e2e.py
│   └── test_05_provisioning_onboarding.py
│
├── openbao/                   # OpenBao 오픈소스 시크릿/SSH CA 설정 & 초기화
├── boundary/                  # HashiCorp Boundary Zero-Trust 설정
└── scripts/                   # 중앙 헬스체크 및 GitOps 시딩
    ├── init-semaphore.sh      # Semaphore UI GitOps 자동 시딩
    ├── healthcheck.sh         # 각 컴포넌트 헬스체크
    └── validate-specs.py      # 3-Way Traceability 검증기
```

---

## 4. 상세 문서 링크

- 🧪 [3-Way Traceability 매트릭스 리포트](file:///home/ppzxc/projects/overseer/docs/TRACEABILITY_MATRIX.md)
- 🔐 [컨트롤 플레인 스펙 (`docs/control-plane/`)](file:///home/ppzxc/projects/overseer/docs/control-plane/INDEX.md)
- 🧪 [E2E 시스템 통합 테스트 가이드](file:///home/ppzxc/projects/overseer/docs/tests/E2E_TESTING_GUIDELINE.md)
- 🌐 [Node-Provisioner Ansible GitOps 저장소](https://github.com/ppzxc/node-provisioner)
