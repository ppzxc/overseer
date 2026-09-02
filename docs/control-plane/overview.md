# Central Control Plane Specification

중앙 컨트롤 플레인(Docker Compose)은 OpenBao(SSH CA & 시크릿 관리), HashiCorp Boundary(Zero-Trust 접근 제어), PostgreSQL(DB)로 구성됩니다.

---

## 컨트롤 플레인 태스크 매트릭스 (Control Plane Task Matrix)

| Spec ID | 컴포넌트 / 태스크 명칭 (Task Name) | 구현 위치 (Implementation) | 검증 대상 (Verification Scope) |
|---|---|---|---|
| `CTRL-001` | `PostgreSQL Database Backend Service` | `compose.yml` | 포트 5432 리스닝 및 pg_isready 헬스체크 |
| `CTRL-002` | `Overseer Bridge Network Isolation` | `compose.yml` | overseer-net 브릿지 네트워크 격리 |
| `CTRL-003` | `Automated Full Stack Bootstrap` | `Makefile` | 원클릭 일괄 기동 및 헬스 대기 워크플로우 (`make up`, `make bootstrap`) |
| `CTRL-004` | `Ansible Semaphore Web UI and Orchestrator service` | `compose.yml` | 포트 3000 Semaphore Web UI 및 PostgreSQL 백엔드 연동 |
| `CTRL-005` | `Automated Semaphore Project and Template Seeding` | `scripts/init-semaphore.sh` | Semaphore REST API 기반 프로젝트/인벤토리/플레이북 템플릿 자동 프로비저닝 |
| `BAO-CTRL-001` | `OpenBao Server Initialization and Unseal` | `openbao/config/openbao.hcl` | 포트 8200 HTTP API 및 unseal 상태 |
| `BAO-CTRL-002` | `OpenBao SSH CA Secrets Engine Mount` | `openbao/scripts/init-openbao-ssh-ca.sh` | ssh-client-signer 마운트 및 CA 공개키 생성 |
| `BAO-CTRL-003` | `OpenBao SSH User Certificate Signing Role` | `openbao/scripts/init-openbao-ssh-ca.sh` | infra-admin-role 서명 엔드포인트 및 단기 인증서 발급 |
| `BND-CTRL-001` | `Boundary Controller Database and API` | `boundary/config/controller.hcl` | 포트 9200 API 및 PostgreSQL DB 마이그레이션 |
| `BND-CTRL-002` | `Boundary Cluster Communications` | `boundary/config/controller.hcl` | 포트 9201 Controller 클러스터 통신 |
| `BND-CTRL-003` | `Boundary Worker Proxy Gateway` | `boundary/config/worker.hcl` | 포트 9202 Worker 프록시 게이트웨이 |
| `ONBOARD-001` | `Greenfield Server Baseline Provisioning Workflow` | `docs/PROVISIONING_AND_MIGRATION_GUIDELINE.md` | 신규 서버 베이스라인, SSH CA, Boundary 타겟 및 OTel Collector 단일 관제 통합 주입 |
| `ONBOARD-002` | `Brownfield Legacy Server 3-Stage Migration and Lockout Safety` | `docs/PROVISIONING_AND_MIGRATION_GUIDELINE.md` | 활성 포트 사전 조사, 레거시 node_exporter 정리, SSH 접속 선검증 후 패스워드 차단 및 방화벽 활성화 |
