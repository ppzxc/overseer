# Central Control Plane Specification

중앙 컨트롤 플레인(Docker Compose)은 HCP Vault(SSH CA & 시크릿 관리), HashiCorp Boundary(Zero-Trust 접근 제어), PostgreSQL(DB), Prometheus(모니터링)로 구성됩니다.

---

## 컨트롤 플레인 태스크 매트릭스 (Control Plane Task Matrix)

| Spec ID | 컴포넌트 / 태스크 명칭 (Task Name) | 구현 위치 (Implementation) | 검증 대상 (Verification Scope) |
|---|---|---|---|
| `CTRL-001` | `PostgreSQL Database Backend Service` | `docker-compose.yml` | 포트 5432 리스닝 및 pg_isready 헬스체크 |
| `CTRL-002` | `Overseer Bridge Network Isolation` | `docker-compose.yml` | overseer-net 브릿지 네트워크 격리 |
| `CTRL-003` | `Automated Full Stack Bootstrap` | `scripts/bootstrap.sh` | 원클릭 일괄 기동 및 헬스 대기 워크플로우 |
| `VAULT-CTRL-001` | `Vault Server Initialization and Unseal` | `vault/config/vault.hcl` | 포트 8200 HTTP API 및 unseal 상태 |
| `VAULT-CTRL-002` | `Vault SSH CA Secrets Engine Mount` | `vault/scripts/init-vault-ssh-ca.sh` | ssh-client-signer 마운트 및 CA 공개키 생성 |
| `VAULT-CTRL-003` | `Vault SSH User Certificate Signing Role` | `vault/scripts/init-vault-ssh-ca.sh` | infra-admin-role 서명 엔드포인트 및 단기 인증서 발급 |
| `BND-CTRL-001` | `Boundary Controller Database and API` | `boundary/config/controller.hcl` | 포트 9200 API 및 PostgreSQL DB 마이그레이션 |
| `BND-CTRL-002` | `Boundary Cluster Communications` | `boundary/config/controller.hcl` | 포트 9201 Controller 클러스터 통신 |
| `BND-CTRL-003` | `Boundary Worker Proxy Gateway` | `boundary/config/worker.hcl` | 포트 9202 Worker 프록시 게이트웨이 |
| `PROM-CTRL-001` | `Prometheus Server Health and API` | `docker-compose.yml` | 포트 9090 HTTP 헬스체크 엔드포인트 |
| `PROM-CTRL-002` | `Prometheus Control Plane and Node Scrape Config` | `prometheus/prometheus.yml` | Vault 및 IDC Node Exporter 수집 잡(Job) 정의 |
