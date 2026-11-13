# Central Control Plane Specification

중앙 컨트롤 플레인(Docker Compose)은 OpenBao(SSH CA 및 시크릿 관리)와 Semaphore UI(Ansible GitOps 오케스트레이션)로 구성됩니다. 운영 Compose 파일은 `/opt/services/openbao/compose.yml`, `/opt/services/semaphore/compose.yml`에 각각 둡니다. OpenBao 설정과 Raft 데이터는 `/data/openbao/config`, `/data/openbao/data`에 저장하고, Semaphore 설정·SQLite 데이터·작업 경로는 `/data/semaphore/config`, `/data/semaphore/data`, `/data/semaphore/work`에 저장합니다.
OpenBao는 로컬 Shamir 또는 GCP Cloud KMS Auto-Unseal을 지원합니다.

---

## 컨트롤 플레인 태스크 매트릭스 (Control Plane Task Matrix)

| Spec ID | 컴포넌트 / 태스크 명칭 (Task Name) | 구현 위치 (Implementation) | 검증 대상 (Verification Scope) |
|---|---|---|---|
| `CTRL-001` | `Semaphore SQLite Persistent Storage` | `semaphore/compose.yml` | `/data/semaphore/data` SQLite 저장과 분리된 작업 디렉터리 |
| `CTRL-002` | `Overseer Bridge Network Isolation` | `openbao/compose.yml`, `semaphore/compose.yml` | 외부 backend 네트워크를 통한 서비스 연결 |
| `CTRL-003` | `Automated Full Stack Bootstrap` | `Makefile` | 원클릭 일괄 기동 및 헬스 대기 워크플로우 (`make up`, `make bootstrap`) |
| `CTRL-004` | `Ansible Semaphore Web UI and Orchestrator service` | `semaphore/compose.yml` | 포트 3000 UI, SQLite 백엔드, Semaphore 메모리 4GiB 한도, Ansible Python 의존성 및 네트워크 백업 볼륨 |
| `CTRL-005` | `Automated Semaphore Project and Template Seeding` | `scripts/init-semaphore.sh` | Semaphore REST API 기반 프로젝트/인벤토리/플레이북 템플릿 시딩 및 기존 템플릿 정합성 갱신 |
| `CTRL-006` | `Automated Pre-Flight Prerequisites Validator` | `scripts/orchestrator.py` | 필수 CLI 도구, Docker 비루트 권한, 데이터 디렉토리 쓰기 권한, 포트 충돌 사전 검증 (`make preflight`) |
| `CTRL-007` | `OpenBao Seal and KMS Backend Configuration Profiles` | `scripts/orchestrator.py` | Local Shamir 및 GCP Cloud KMS 프로파일 주입 (`make configure-seal`) |
| `CTRL-008` | `Production Target Deployment and Backup-Ready Packaging` | `scripts/orchestrator.py` | Git/테스트/일반 문서는 제외하고 운영 필수 파일과 이관 런북을 배포 디렉터리(`/opt/services/overseer`)에 복제 |
| `CTRL-009` | `Semaphore PostgreSQL to SQLite Data Migration` | `scripts/migrate-semaphore-postgres-to-sqlite.py` | 동일 버전 스키마 검사, 테이블 복사, 행 수/체크섬, SQLite 무결성 및 외래 키 검증 |
| `BAO-CTRL-001` | `OpenBao Server Initialization and Unseal` | `openbao/config/openbao.hcl` (운영 파일: `/data/openbao/config/openbao.hcl`) | 포트 8200 HTTP API 및 unseal 상태 |
| `BAO-CTRL-002` | `OpenBao SSH CA Secrets Engine Mount` | `openbao/scripts/init-openbao-ssh-ca.sh` | ssh-client-signer 마운트 및 CA 공개키 생성 |
| `BAO-CTRL-003` | `OpenBao SSH User Certificate Signing Role` | `openbao/scripts/init-openbao-ssh-ca.sh` | infra-admin-role 서명 엔드포인트 및 단기 인증서 발급 |
| `ONBOARD-001` | `Greenfield Server Baseline Provisioning Workflow` | `docs/PROVISIONING_AND_MIGRATION_GUIDELINE.md` | 신규 서버 베이스라인, OpenBao SSH CA 및 OTel Collector 설정 |
| `ONBOARD-002` | `Brownfield Legacy Server 3-Stage Migration and Lockout Safety` | `docs/PROVISIONING_AND_MIGRATION_GUIDELINE.md` | 활성 포트 사전 조사, 레거시 node_exporter 정리, SSH 접속 선검증 후 패스워드 차단 및 방화벽 활성화 |
