# Control Plane Specification Index

중앙 컨트롤 플레인(OpenBao, Semaphore UI)의 아키텍처 및 상세 스펙입니다.

- 📄 [컨트롤 플레인 컴포넌트 상세 스펙 (`docs/control-plane/overview.md`)](file:///home/ppzxc/projects/overseer/docs/control-plane/overview.md)
  - `CTRL-001` ~ `CTRL-003`: Semaphore SQLite 저장소 & Compose 오케스트레이션
  - `CTRL-004` ~ `CTRL-005`: Semaphore UI & GitOps 자동화 시딩
  - `BAO-CTRL-001` ~ `BAO-CTRL-003`: OpenBao Server & SSH CA
  - `ONBOARD-001` ~ `ONBOARD-002`: Greenfield & Brownfield Provisioning Onboarding
- 📄 [Semaphore PostgreSQL → SQLite 운영 이관 런북](semaphore-postgres-to-sqlite.md)
  - `CTRL-009`: 사전 백업, 동일 버전 SQLite 초기화, 데이터 복사, 검증, 롤백
