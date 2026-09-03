# Overseer: IDC Infrastructure Zero-Trust Control Plane

**Overseer**는 소-중규모 IDC 온프레미스 인프라 환경의 중앙 제어 플레인(OpenBao v2.6.2, HashiCorp Boundary 0.21.3, Semaphore UI v2.19.12, PostgreSQL 15)을 일괄 오케스트레이션하고, 독립된 Ansible GitOps 저장소(`node-provisioner`)를 통해 온프레미스 노드 프로비저닝을 제어하는 Docker Compose 기반 중앙 컨트롤 플레인입니다.

---

## 1. 주요 구성 컴포넌트

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                    Overseer Central Control Plane (Docker Compose)          │
│                                                                             │
│  ┌──────────────────┐    ┌──────────────────┐    ┌───────────────────────┐  │
│  │ OpenBao (v2.6.2) │    │ Boundary(0.21.3) │    │ Semaphore (v2.19.12)  │  │
│  │ (SSH CA, Web UI) │    │ (Zero-Trust IAM) │    │ & GitOps Orchestrator │  │
│  │ [Shamir / GCP-KMS│    │ [AEAD / GCP-KMS] │    └───────────▲───────────┘  │
│  └────────┬─────────┘    └────────┬─────────┘                │              │
│           │                       │                          │              │
│           └──────────────┬────────▼──────────────────────────┴───────────┐  │
│                          │     PostgreSQL 15 (Boundary & Semaphore DB)   │  │
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

### 0) 로컬 환경 설정 및 점진적 환경변수 활성화 (Lazy Lifecycle)
`.env.example` 템플릿에는 사용하지 않는 옵션 변수(포트 바인딩, GCP Cloud KMS 등)가 기본 주석(`#`) 처리되어 있으며, `make bootstrap` 단계에서 선택한 모드에 따라 필요한 변수만 주석이 해제(`uncomment`)되고 난수 암호화 키가 자동 주입됩니다.
```bash
# 컨트롤 플레인 환경변수 템플릿 복사
cp .env.example .env
```

### 1) 중앙 컨트롤 플레인 부트스트랩 및 서비스 제어
```bash
# [전체 통합] 전체 스택 기동 및 초기화 (운영 경로 /opt/services/overseer 자동 복제 배포 지원)
make bootstrap        # 또는 make up (TARGET_DIR=/opt/services/overseer 지정 가능)

# [운영 필수 파일 동기화/배포만 실행]
make production-sync  # 운영 필수 구성요소만 대상 경로로 선별 복제 (비운영 파일 제외)

# [KMS 프로파일 변경/주입]
make configure-seal   # Local Shamir 또는 GCP Cloud KMS 프로파일 대화형/자동 적용

# [전체 상태 확인 / 중지]
make status           # PostgreSQL, OpenBao, Boundary, Semaphore 헬스체크
make down             # 전체 서비스 중지

# [개별 서비스 기동/중지/초기화]
make start-openbao    # OpenBao만 기동 및 SSH CA 언실/초기화
make start-boundary   # Boundary만 기동 및 DB 마이그레이션
make start-semaphore  # Semaphore만 기동 및 GitOps 템플릿 시딩
make stop-boundary    # Boundary 컨테이너 중지
```

#### 마스터 키 관리 & 스토리지 프로파일 (3가지 모드):
- **[1] Local .env Persisted (`KEY_MANAGEMENT_PROFILE=local`, 기본값)**:
  - OpenBao Shamir Unseal 키를 로컬 디스크(`/data/openbao/openbao-init.json`)에 저장하고 Boundary AEAD 키 및 Semaphore 키를 `.env`에 보관하여 호스트 재부팅 시 완전 자동 언실/기동됩니다.
- **[2] Zero-Knowledge Manual (`KEY_MANAGEMENT_PROFILE=manual`)**:
  - 초기화 시 마스터 키 5종(Boundary AEAD 3종, Semaphore 암호화 키, OpenBao Shamir 키)을 터미널에 1회 백업 박스로 출력한 후 **`.env` 파일 및 디스크에서 즉시 완전 삭제(Zero-Knowledge Wipe)**합니다.
  - **호스트 재부팅/재시작 시 환경변수 주입 방법**:
    - **대화형 입력**: `make up` 또는 `make bootstrap` 실행 시 키 누락을 감지하고 마스킹된 터미널 프롬프트를 통해 세션 메모리로 즉시 주입받습니다.
    - **쉘 환경변수 주입 (비대화형/스크립트)**: 기동 전 터미널 세션에 환경변수를 export 합니다:
      ```bash
      export BOUNDARY_KMS_AEAD_ROOT_KEY="<YOUR_ROOT_KEY>"
      export BOUNDARY_KMS_AEAD_WORKER_AUTH_KEY="<YOUR_WORKER_KEY>"
      export BOUNDARY_KMS_AEAD_RECOVERY_KEY="<YOUR_RECOVERY_KEY>"
      export SEMAPHORE_ACCESS_KEY_ENCRYPTION="<YOUR_SEMAPHORE_KEY>"
      export OPENBAO_UNSEAL_KEY="<YOUR_OPENBAO_UNSEAL_KEY>" # 또는 OpenBao Web UI에서 언실
      make up
      ```
- **[3] External Cloud KMS (`KEY_MANAGEMENT_PROFILE=gcpkms`)**:
  - Google Cloud KMS Cloud HSM 키를 사용하여 OpenBao 및 Boundary를 자동 언실하며 호스트에 로컬 키를 저장하지 않습니다.

#### 호스트 포트 바인딩 모드:
- **호스트 노출 모드 (`EXPOSE_PORTS=true`, 기본값)**: `compose.override.yml`이 동적 생성되어 호스트 `0.0.0.0` 인터페이스에 서비스 포트와 1:1 일치하는 포트 매핑을 바인딩합니다.
  - **OpenBao Web UI / API**: `0.0.0.0:8200:8200` ([http://localhost:8200](http://localhost:8200))
  - **Boundary Admin UI / API**: `0.0.0.0:9200:9200` ([http://localhost:9200](http://localhost:9200)), Cluster: `9201`, Worker: `9202`
  - **Semaphore Ansible Web UI**: `0.0.0.0:3000:3000` ([http://localhost:3000](http://localhost:3000), 초기 계정: `admin` / `semaphoreadmin`)
- **내부망 전용 모드 (`EXPOSE_PORTS=false`)**: `compose.override.yml`이 제외되어 호스트 포트가 전혀 노출되지 않으며, `backend` 브릿지 네트워크로만 안전하게 통신합니다.

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
├── compose.yml                # 기본 컨트롤 플레인 정의 (포트 미노출 베이스라인)
├── compose.override.yml       # [동적 생성] 0.0.0.0 1:1 호스트 포트 바인딩 오버라이드
├── .env.example               # 점진적 주석 해제 지원 환경 변수 템플릿
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
│   ├── test_05_provisioning_onboarding.py
│   ├── test_06_seal_matrix.py
│   └── test_07_production_deployment.py
│
├── openbao/                   # OpenBao 오픈소스 시크릿/SSH CA 설정 & 초기화
│   ├── config/profiles/       # Local Shamir 및 GCP Cloud KMS 프로파일
│   └── scripts/               # SSH CA 엔진 활성화 및 Auto-Unseal 호환 스크립트
├── boundary/                  # HashiCorp Boundary Zero-Trust 설정
│   ├── config/profiles/       # Controller / Worker Local AEAD 및 GCP KMS 프로파일
│   └── scripts/               # Boundary DB 초기화 스크립트
└── scripts/                   # 중앙 헬스체크 및 GitOps 시딩
    ├── orchestrator.py        # 통합 라이프사이클 및 SEAL/Port/Env 주입 오케스트레이터
    ├── init-semaphore.sh      # Semaphore UI GitOps 자동 시딩
    └── validate-specs.py      # 3-Way Traceability 검증기
```

---

## 4. 상세 문서 링크

- 🧪 [3-Way Traceability 매트릭스 리포트](file:///home/ppzxc/projects/overseer/docs/tests/TRACEABILITY_MATRIX.md)
- 🔐 [컨트롤 플레인 스펙 (`docs/control-plane/`)](file:///home/ppzxc/projects/overseer/docs/control-plane/INDEX.md)
- 🏛️ [ADR-0005: Pluggable Seal/Unseal Backend Profiles](file:///home/ppzxc/projects/overseer/docs/adr/0005-pluggable-seal-unseal-backend-profiles.md)
- 🏛️ [ADR-0006: Modular 1:1 Host Port Binding and Lazy .env Variable Lifecycle](file:///home/ppzxc/projects/overseer/docs/adr/0006-compose-override-port-binding-and-env-lifecycle.md)
- 🧪 [E2E 시스템 통합 테스트 가이드](file:///home/ppzxc/projects/overseer/docs/tests/E2E_TESTING_GUIDELINE.md)
- 🌐 [Node-Provisioner Ansible GitOps 저장소](https://github.com/ppzxc/node-provisioner)
