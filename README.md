# Overseer: IDC Infrastructure Control Plane

**Overseer**는 소·중규모 IDC의 SSH 인증서 발급과 Ansible 기반 서버 관리를 제공하는 Docker Compose 프로젝트입니다. OpenBao가 SSH CA와 시크릿을 관리하고, Semaphore UI가 독립된 `node-provisioner` Git 저장소의 플레이북을 실행합니다.

## 구성

| 서비스 | 역할 | 영속 데이터 |
|---|---|---|
| OpenBao 2.6.2 | SSH CA, 시크릿 관리, Shamir 또는 GCP Cloud KMS seal | `${DATA_DIR}/openbao` |
| Semaphore UI 2.19.12 | Ansible GitOps UI, 스케줄러, 작업 실행 | `${DATA_DIR}/semaphore-db` (SQLite) |
| Semaphore 작업 캐시 | 체크아웃한 저장소와 작업 디렉터리 | `${DATA_DIR}/semaphore` |

Semaphore는 SQLite를 기본 저장소로 사용합니다. 데이터베이스 파일은 `/var/lib/semaphore` 볼륨에 저장하며, 작업 캐시와 분리되어 있습니다. 단일 Overseer 인스턴스에 맞춘 구성입니다.

```text
Operator ──> OpenBao (SSH CA) ──> IDC servers
    │
    └──────> Semaphore ──pull──> node-provisioner Git repository
                    └──────────> IDC servers
```

## 시작

```bash
cp .env.example .env
make bootstrap
```

`make bootstrap`은 설정을 확인하고 OpenBao와 Semaphore를 시작한 뒤 Semaphore의 GitOps 프로젝트와 템플릿을 시딩합니다. 기본 서비스 포트는 OpenBao `8200`, Semaphore `3000`입니다. 호스트에 포트를 열지 않으려면 `.env`에서 `EXPOSE_PORTS=false`를 설정합니다.

주요 관리 명령:

```bash
make status
make logs
make down
make start-openbao
make start-semaphore
make production-sync TARGET_DIR=/opt/services/overseer
```

`make configure-seal`에서 OpenBao의 로컬 Shamir 또는 GCP Cloud KMS 프로파일을 설정할 수 있습니다. Semaphore 키스토어 암호화 키(`SEMAPHORE_ACCESS_KEY_ENCRYPTION`)는 SQLite DB의 자격증명을 읽는 데 필요하므로 기존 값을 보존하세요.

## 기존 PostgreSQL 데이터에서 전환할 때

현재 Semaphore의 PostgreSQL 데이터를 SQLite로 자동 복사하는 기능은 없습니다. `SEMAPHORE_DB_DIALECT=sqlite`로 바꾸면 새 SQLite 데이터베이스가 만들어지며, 기존 PostgreSQL 데이터는 그곳에 나타나지 않습니다. 먼저 PostgreSQL을 백업하고, 데이터 이전을 별도로 완료한 뒤 SQLite로 전환하세요. 기존 PostgreSQL 데이터 디렉터리는 이 저장소의 구성 변경이나 bootstrap에서 삭제하지 않습니다.

## 검증

```bash
make spec-check
make test-e2e
```

## 문서 및 저장소

- [컨트롤 플레인 스펙](docs/control-plane/INDEX.md)
- [테스트 가이드](docs/tests/INDEX.md)
- [프로비저닝 및 마이그레이션 가이드](docs/PROVISIONING_AND_MIGRATION_GUIDELINE.md)
- [node-provisioner Ansible 저장소](https://github.com/ppzxc/node-provisioner)
