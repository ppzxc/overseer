# Overseer: IDC Infrastructure Control Plane

**Overseer**는 소·중규모 IDC의 SSH 인증서 발급과 Ansible 기반 서버 관리를 제공하는 Docker Compose 프로젝트입니다. OpenBao가 SSH CA와 시크릿을 관리하고, Semaphore UI가 독립된 `node-provisioner` Git 저장소의 플레이북을 실행합니다.

## 구성

| 서비스 | 역할 | 영속 데이터 |
|---|---|---|
| OpenBao 2.6.2 | SSH CA, 시크릿 관리, Shamir 또는 GCP Cloud KMS seal | `${DATA_DIR}/openbao` |
| Semaphore UI 2.19.12 | Ansible GitOps UI, 스케줄러, 작업 실행 (메모리 한도 4GiB) | `${DATA_DIR}/semaphore-db` (SQLite) |
| Semaphore 작업 캐시 | 체크아웃한 저장소와 작업 디렉터리 | `${DATA_DIR}/semaphore` |
| 네트워크 장비 설정 백업 | Cisco 및 FortiGate 설정 백업 파일 | `${DATA_DIR}/network-backups` |

OpenBao와 Semaphore는 각각 `openbao/compose.yml`, `semaphore/compose.yml`에서 별도로 관리합니다. 두 Compose 파일은 `name: app`과 `json-file` 로그 회전(`20m`, 3개 파일)을 사용하고, 공유 외부 `backend` 네트워크에 연결합니다. Compose 프로젝트 `app`은 Forgejo와 공유하므로 `--remove-orphans`를 사용하지 않습니다. 운영 동기화도 기존 Forgejo나 서비스 데이터를 삭제하지 않습니다. 기존 루트 통합 Compose 파일은 제거했습니다.

Semaphore는 SQLite를 기본 저장소로 사용합니다. 데이터베이스 파일은 `/var/lib/semaphore` 볼륨에 저장하며, 작업 캐시와 분리되어 있습니다. Ansible 추가 Python 패키지는 `semaphore/requirements.txt`에서 관리하고 컨테이너의 `/etc/semaphore/requirements.txt`로 연결합니다. Cisco와 FortiGate 백업 파일은 컨테이너의 `/var/backups`에서 `${DATA_DIR}/network-backups`로 영속 저장합니다. 전체 Host Audit 플레이북의 메모리 사용량을 고려해 Semaphore 컨테이너는 4GiB로 제한합니다.

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

`make bootstrap`은 설정을 확인하고 OpenBao와 Semaphore를 각자의 Compose 파일로 시작한 뒤 Semaphore의 GitOps 프로젝트와 템플릿을 시딩합니다. 서비스별 관리는 `make start-openbao`, `make start-semaphore`로 수행합니다. OpenBao는 `backend` 네트워크 안에서만 접근하고, Semaphore UI는 `EXPOSE_PORTS=true`일 때 호스트의 `3000` 포트에 바인딩합니다. 호스트 포트를 닫으려면 `.env`에서 `EXPOSE_PORTS=false`를 설정합니다.

신규 설치는 `.env`의 `SEMAPHORE_ACCESS_KEY_ENCRYPTION`에 `head -c 32 /dev/urandom | base64`로 만든 키를 설정한 뒤 시작합니다. 기존 데이터베이스를 복구하거나 이관할 때에는 기존 키를 그대로 보존합니다. 키를 설정하지 않으면 Compose 시작을 거부합니다.

시딩은 기존 `Overseer Infrastructure` 프로젝트에도 적용됩니다. 현재 유지하는 템플릿의 플레이북과 설정을 갱신하고, 이전 유지보수·드라이런 템플릿은 현재 이름과 플레이북으로 정리합니다. 폐기된 `Provision Overseer Control Plane` 및 `Provision Full Stack (All)` 템플릿은 제거합니다.

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

Semaphore의 PostgreSQL 데이터를 SQLite로 바꾸는 작업은 DB 엔진 변경만으로 완료되지 않습니다. 운영 DB를 백업하고, 동일한 Semaphore 버전으로 초기화한 SQLite DB에 데이터를 복사한 뒤 검증해야 합니다. `ns0266.nanoit.kr`의 계획된 이관은 [운영 이관 런북](docs/control-plane/semaphore-postgres-to-sqlite.md)을 따릅니다. 저장소에는 이관 도구가 포함되어 있으며, PostgreSQL 데이터 디렉터리와 롤백 구성을 보존하도록 안내합니다.

운영 파일 동기화는 두 서비스 Compose 파일과 필요한 런타임 파일만 배포하며 작업공간의 `.env`를 대상 운영 디렉터리에 덮어쓰지 않습니다. `production-sync`는 파일만 동기화하고 컨테이너를 재기동하지 않습니다. 운영 `.env`의 기존 암호화 키와 연결 설정을 유지하세요.

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
