# Overseer: IDC Infrastructure Control Plane

## 1. 프로젝트 개요 (Overview)
**Overseer**는 소-중규모 IDC(온프레미스) 내 사내 인프라를 효율적이고 안전하게 관리하기 위한 **Docker Compose 기반 중앙 컨트롤 플레인**입니다.

- **중앙 컨트롤 플레인 (Control Plane)**: Docker Compose 기반으로 OpenBao(SSH CA & 시크릿 관리), HashiCorp Boundary(Zero-Trust 접근 제어), Semaphore UI(GitOps Ansible 오케스트레이터), PostgreSQL DB를 통합 구동
- **GitOps 자동화 연동**: 독립된 Ansible 프로비저닝 저장소(`node-provisioner`)를 Semaphore UI와 원격 GitOps 파이프라인으로 연결하여 온프레미스 서버들의 프로비저닝 및 유지보수를 웹 UI와 API로 일원화 제어

---

## 2. 핵심 기술 스택 및 아키텍처

| 기술 | 역할 |
|---|---|
| **Docker Compose** | 중앙 컨트롤 플레인(OpenBao, Boundary, Semaphore, Postgres) 일괄 오케스트레이션 |
| **OpenBao** | 중앙 집중형 시크릿 관리, SSH Certificate Authority(CA) 서명, 임시 자격증명 발급 (Linux Foundation Open-Source Vault Fork) |
| **HashiCorp Boundary** | 사내망 노출 없는 안전한 인프라 접근 제어(IAM), 세션 관리 및 감사 로그 |
| **Semaphore UI** | 웹 기반 Ansible 오케스트레이션 및 스케줄러, `node-provisioner` GitOps 파이프라인 연동 |
| **PostgreSQL** | Boundary 및 Semaphore 공유 메타데이터 영구 저장소 |

---

## 3. 디렉토리 구조 (Directory Structure)

```text
overseer/
├── AGENTS.md                  # AI 및 엔지니어 협업 가이드 (본 문서)
├── CONTEXT.md                 # Overseer 도메인 컨텍스트
├── README.md                  # 프로젝트 통합 개요 및 빠른 시작 가이드
├── compose.yml                # [메인] OpenBao, Boundary, Semaphore, Postgres 일괄 기동
├── .env.example               # 환경 변수 템플릿 (DB 자격증명, 토큰, GitOps URL)
├── Makefile                   # 원클릭 통합 제어 인터페이스 (make bootstrap, up, test 등)
│
├── docs/                      # [전역 문서 저장소]
│   ├── control-plane/         # [중앙 컨트롤 플레인 스펙 및 태스크 매트릭스]
│   ├── tests/                 # [테스트 및 검증 가이드라인]
│   │   ├── INDEX.md
│   │   ├── TRACEABILITY_MATRIX.md
│   │   └── E2E_TESTING_GUIDELINE.md
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
│   ├── config/openbao.hcl     # OpenBao 서버 설정 (File storage, TCP Listener, UI)
│   ├── policies/              # OpenBao ACL 정책 정의
│   └── scripts/               # SSH CA 엔진 활성화 및 역할 등록 스크립트
│
├── boundary/                  # HashiCorp Boundary Zero-Trust 설정
│   ├── config/
│   │   ├── controller.hcl     # Boundary Controller 설정 (DB, KMS, API)
│   │   └── worker.hcl         # Boundary Worker 설정 (Proxy, Worker-Auth)
│   └── scripts/               # Boundary DB 초기화 및 타겟 구성 스크립트
│
└── scripts/                   # 중앙 헬스체크 및 GitOps 시딩
    ├── init-semaphore.sh      # Semaphore UI GitOps 프로젝트/템플릿 자동 시딩
    ├── healthcheck.sh         # 각 컴포넌트 헬스체크
    └── validate-specs.py      # 3-Way Traceability 검증기
```

---

## 4. 인프라 운영 및 개발 원칙

1. **Zero-Trust & 최소 권한 원칙**:
   - 루트 직접 SSH 접근을 전면 차단합니다.
   - 정적 SSH 비밀번호/영구 개인키 사용을 지양하고 OpenBao 기반 SSH Certificate 또는 Boundary 기반 접근을 지향합니다.
2. **GitOps 기반 분리 운영**:
   - 중앙 컨트롤 플레인(`overseer`)과 실제 인프라 프로비저닝 코드(`node-provisioner`)는 완전히 분리되어 관리됩니다.
   - Semaphore UI가 원격 Git 저장소를 바라보고 자동으로 최신 코드를 pull하여 실행합니다.
3. **문서 최신화 의무 (Documentation Update)**:
   - 컨트롤 플레인 구성, Docker Compose, 변수, 스크립트 등의 코드/구조를 추가하거나 변경할 때에는 **반드시 `README.md` 및 `docs/`를 즉시 업데이트**하여 형상과 문서가 항상 일치하도록 유지해야 합니다.

---

## Agent skills

### Issue tracker

Tracked via GitHub Issues (`gh` CLI). See `docs/agents/issue-tracker.md`.

### Domain docs

Single-context layout (`CONTEXT.md` and `docs/adr/`). See `docs/agents/domain.md`.

