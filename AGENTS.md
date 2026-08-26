# Overseer: IDC Infrastructure Provisioning & Automation

## 1. 프로젝트 개요 (Overview)
**Overseer**는 소-중규모 IDC(온프레미스) 내 사내 인프라를 효율적이고 안전하게 관리하기 위한 **Docker Compose 기반 중앙 컨트롤 플레인 및 Ansible 프로비저닝 자동화 툴체인**입니다.

- **중앙 컨트롤 플레인 (Control Plane)**: Docker Compose 기반으로 HCP Vault(SSH CA & 시크릿 관리), HashiCorp Boundary(Zero-Trust 접근 제어), PostgreSQL DB, Prometheus 모니터링을 통합 구동
- **기존 인프라 마이그레이션**: 파편화된 기존 온프레미스 서버 환경을 정형화된 코드(IaC) 기반으로 표준화 및 이전
- **신규 서버 프로비저닝**: 신규 하드웨어 및 VM(Hypervisor)의 초기 셋업(OS 보안, 네트워크, 방화벽, 계정, 에이전트) 자동화
- **유지보수 및 형상 관리**: 정기 보안 패치, 모니터링 에이전트 업데이트, 멱등성 기반 상태 보장

---

## 2. 핵심 기술 스택 및 아키텍처

| 기술 | 역할 |
|---|---|
| **Docker Compose** | 중앙 컨트롤 플레인(Vault, Boundary, Postgres, Prometheus) 일괄 오케스트레이션 |
| **HCP Vault** | 중앙 집중형 시크릿 관리, SSH Certificate Authority(CA) 서명, 임시 자격증명 발급 |
| **HashiCorp Boundary** | 사내망 노출 없는 안전한 인프라 접근 제어(IAM), 세션 관리 및 감사 로그 |
| **Ansible** | 온프레미스 노드 설정 자동화, 멱등성 기반 형상 관리 및 프로비저닝 |
| **Prometheus** | 온프레미스 노드(`node_exporter`) 및 컨트롤 플레인 메트릭 수집 |

---

## 3. 디렉토리 구조 (Directory Structure)

```text
overseer/
├── AGENTS.md                  # AI 및 엔지니어 협업 가이드 (본 문서)
├── README.md                  # 프로젝트 통합 개요 및 빠른 시작 가이드
├── docker-compose.yml         # [메인] Vault, Boundary, Postgres, Prometheus 일괄 기동
├── .env.example               # 환경 변수 템플릿 (DB 자격증명, 토큰, KMS 키)
├── Makefile                   # 원클릭 통합 제어 인터페이스 (make bootstrap, up, test 등)
│
├── docs/                      # [전역 문서 저장소]
│   ├── control-plane/         # [중앙 컨트롤 플레인 스펙]
│   ├── ansible/               # [Role별 태스크 스펙 및 3단 추적 매트릭스]
│   ├── tests/                 # [테스트 및 검증 세분화 가이드라인]
│   │   ├── INDEX.md
│   │   ├── TRACEABILITY_MATRIX.md
│   │   ├── E2E_TESTING_GUIDELINE.md
│   │   └── ANSIBLE_TESTING_GUIDELINE.md
│   └── PROVISIONING_AND_MIGRATION_GUIDELINE.md # 온프레미스 프로비저닝 & 마이그레이션 가이드
│
├── tests/                     # [E2E 시스템 통합 테스트 스위트 (Pytest + Testinfra)]

│   ├── conftest.py
│   ├── test_01_control_plane.py
│   ├── test_02_vault_ssh_ca.py
│   ├── test_03_boundary.py
│   └── test_04_ansible_e2e.py
│
├── vault/                     # HCP / Self-hosted Vault 설정 & 초기화

│   ├── config/vault.hcl       # Vault 서버 설정 (File storage, TCP Listener, UI)
│   ├── policies/              # Vault ACL 정책 정의
│   └── scripts/               # SSH CA 엔진 활성화 및 역할 등록 스크립트
│
├── boundary/                  # HashiCorp Boundary Zero-Trust 설정
│   ├── config/
│   │   ├── controller.hcl     # Boundary Controller 설정 (DB, KMS, API)
│   │   └── worker.hcl         # Boundary Worker 설정 (Proxy, Worker-Auth)
│   └── scripts/               # Boundary DB 초기화 및 타겟 구성 스크립트
│
├── prometheus/                # Prometheus 설정 (컨트롤 플레인 & 노드 수집)
│   └── prometheus.yml
│
├── scripts/                   # 중앙 부트스트랩 및 헬스체크
│   ├── bootstrap.sh           # 전체 스택 기동 및 초기화 자동화
│   └── healthcheck.sh         # 각 컴포넌트 헬스체크
│
└── ansible/                   # [온프레미스 노드 프로비저닝 레이어]
    ├── ansible.cfg            # Ansible 기본 설정 (인벤토리 경로, SSH 파이프라이닝 등)
    ├── Dockerfile & docker-run.sh # Ansible 실행 컨테이너 환경
    ├── inventory/             # IDC 노드 인벤토리 및 그룹/호스트 변수
    ├── playbooks/             # provision.yml, maintenance.yml, site.yml
    ├── roles/                 # common, security, vault_ssh_ca, boundary_target, monitoring
    └── molecule/              # Molecule Rocky Linux / Ubuntu 통합 테스트 시나리오
```

---

## 4. 인프라 운영 및 개발 원칙

1. **멱등성(Idempotency) 보장**:
   - 모든 Ansible 태스크는 반복 실행해도 동일한 결과를 보장해야 합니다.
   - `shell`/`command` 모듈 사용 시 반드시 `creates`, `removes` 또는 `changed_when` 조건을 명시합니다.
2. **Zero-Trust & 최소 권한 원칙**:
   - 루트 직접 SSH 접근을 전면 차단합니다.
   - 정적 SSH 비밀번호/영구 개인키 사용을 지양하고 HCP Vault 기반 SSH Certificate 또는 Boundary 기반 접근을 지향합니다.
3. **가독성 및 모듈화**:
   - 단일 플레이북에 모든 작업을 넣지 않고 Role 단위로 분리하여 유지 관리성을 극대화합니다.
   - 변수는 `group_vars` 및 `host_vars`로 분리하여 환경 종속적인 값을 하드코딩하지 않습니다.
4. **안전한 레거시 마이그레이션 원칙 (Safe Migration Checklist)**:
   - **SSH 락아웃(Lockout) 방지**: Vault SSH CA 및 관리자 키 동작이 확인되기 전에 비밀번호 로그인을 차단하지 않습니다.
   - **포트 사전 식별**: 방화벽 활성화 전 `ss -tulpn` 등으로 기존 LISTEN 포트를 필수 수집하여 `host_vars`에 정의합니다.
   - **사전 시뮬레이션**: 신규 적용 전 반드시 `--check --diff`로 변경점을 사전 검증합니다.
5. **문서 최신화 의무 (Documentation Update)**:
   - Ansible 플레이북, 역할(Roles), 인벤토리, Docker Compose, 변수 등의 코드/구조를 추가하거나 변경할 때에는 **반드시 `README.md` 및 `ansible/README.md`를 즉시 업데이트**하여 형상과 문서가 항상 일치하도록 유지해야 합니다.

---

## Agent skills

### Issue tracker

Tracked via GitHub Issues (`gh` CLI). See `docs/agents/issue-tracker.md`.

### Domain docs

Single-context layout (`CONTEXT.md` and `docs/adr/`). See `docs/agents/domain.md`.

