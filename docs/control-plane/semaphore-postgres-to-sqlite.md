# Semaphore PostgreSQL to SQLite 운영 이관

이 절차는 `ns0266.nanoit.kr`의 Semaphore `v2.19.12` 데이터를 같은 버전의 SQLite 스키마로 복사하고, 운영 Compose에서 PostgreSQL 및 Boundary를 제외하기 위한 점검 런북입니다. 앱 데이터베이스 엔진 전환은 Semaphore가 자동으로 수행하지 않습니다. 컷오버 동안 Semaphore와 Boundary를 중지하고 PostgreSQL 데이터와 기존 운영 구성을 보존합니다.

현재 작업 환경에서는 `ns0266.nanoit.kr` SSH 연결을 사용할 수 없었습니다. 실제 운영 이관은 이 문서와 도구를 운영 호스트에서 실행하고 완료 기준을 모두 통과한 뒤에만 완료로 처리합니다.

## 사전 조건

- 긴 점검 시간과 운영 호스트 접근 권한을 확보합니다.
- 구버전/신버전 모두 `semaphoreui/semaphore:v2.19.12`를 사용합니다.
- `SEMAPHORE_ACCESS_KEY_ENCRYPTION` 기존 값을 그대로 유지합니다. 이 값을 바꾸면 저장된 키스토어 자격증명을 복호화하지 못할 수 있습니다.
- 키가 `.env`에 저장되지 않는 수동 키 관리 모드라면, 안전한 키 보관본에서 기존 값을 대화형으로 주입합니다. 새 키를 만들지 않습니다.
- 새 Compose 파일의 `${DATA_DIR}/semaphore/data/database.sqlite`와 체크섬 보고서 저장 공간을 확보합니다.
- 호스트 Python 3 및 격리된 가상환경을 준비하고 psycopg 3를 설치합니다:

  ```bash
  python3 -m venv /tmp/semaphore-migration-venv
  /tmp/semaphore-migration-venv/bin/pip install 'psycopg[binary]>=3.2,<4'
  ```

- PostgreSQL 연결 DSN은 `SEMAPHORE_PG_DSN` 환경변수로만 전달합니다. DSN이나 비밀번호를 명령 인자, 문서, 로그에 기록하지 않습니다.

## 중단 전 준비 및 백업

1. 현재 Semaphore Compose 파일(`/opt/services/semaphore/compose.yml`), 운영 `.env`, 그리고 PostgreSQL 서비스 설정을 권한 제한된 백업 디렉터리에 복사합니다. `.env`에는 비밀값이 있으므로 권한을 `0600`으로 제한합니다.
2. Semaphore 작업 큐와 실행 중인 작업이 비었는지 UI/API에서 확인합니다. 이후 Semaphore와 Boundary를 중지합니다.
3. 현재 PostgreSQL 데이터베이스 전체를 custom 형식으로 백업합니다. 기존 운영 환경의 실제 컨테이너명, 사용자, DB명을 사용합니다.

   ```bash
   BACKUP_DIR=/secure/backup/path
   docker exec postgres-container pg_dump -U semaphore -Fc semaphore > "$BACKUP_DIR/semaphore-postgres.dump"
   pg_restore --list "$BACKUP_DIR/semaphore-postgres.dump" >/dev/null
   sha256sum "$BACKUP_DIR/semaphore-postgres.dump" > "$BACKUP_DIR/semaphore-postgres.dump.sha256"
   sha256sum --check "$BACKUP_DIR/semaphore-postgres.dump.sha256"
   ```

4. 백업을 별도 임시 DB 또는 격리된 PostgreSQL에 실제 복원합니다. 충분한 공간을 확보하고 관리자 계정으로 실행합니다.

   ```bash
   docker exec postgres-container createdb -U postgres semaphore_restore_check
   docker exec -i postgres-container pg_restore -U postgres --no-owner -d semaphore_restore_check - < "$BACKUP_DIR/semaphore-postgres.dump"
   docker exec postgres-container dropdb -U postgres semaphore_restore_check
   ```

   복원 명령이 실패하면 이관을 진행하지 않습니다. 임시 DB를 삭제하기 전에 복원 로그를 확인하고, 필요한 경우 테이블 행 수도 운영 DB와 대조합니다.
5. PostgreSQL을 정상 종료한 뒤 `/data/postgres` 전체를 별도 보존 경로에 복사하거나 스냅샷합니다. 백업이 끝나면 기존 데이터 디렉터리를 삭제하거나 초기화하지 않습니다.
6. PostgreSQL을 다시 시작해 데이터 복사 중 읽을 수 있게 합니다. Semaphore와 Boundary는 계속 중지 상태로 둡니다.

운영 PostgreSQL 인스턴스에 임시 DB를 만들 수 없다면 운영과 분리된 임시 PostgreSQL 인스턴스에서 복원을 검증합니다. 실제 복원 검증을 할 수 없으면 컷오버를 완료로 판정하지 않습니다.

## SQLite 초기화 및 데이터 복사

1. 변경된 저장소 파일을 운영 경로에 동기화하되 아직 전체 bootstrap은 실행하지 않습니다. 기존 `.env`는 보존합니다. 배포 동기화는 더 이상 소스 작업공간의 `.env`를 운영 경로에 복사하지 않습니다.
2. Semaphore를 새 SQLite Compose 설정으로 단독 기동해 앱이 자체 마이그레이션으로 빈 스키마를 만드도록 합니다. PostgreSQL은 별도 컨테이너로 계속 실행합니다.

   ```bash
   cd /home/ppzxc/services/overseer
   read -rsp 'Existing Semaphore encryption key: ' SEMAPHORE_ACCESS_KEY_ENCRYPTION; echo
   export SEMAPHORE_ACCESS_KEY_ENCRYPTION
   docker compose --project-directory /opt/services/semaphore --env-file /home/ppzxc/services/overseer/.env -f /opt/services/semaphore/compose.yml up -d semaphore
   docker compose --project-directory /opt/services/semaphore --env-file /home/ppzxc/services/overseer/.env -f /opt/services/semaphore/compose.yml logs --no-color semaphore
   docker compose --project-directory /opt/services/semaphore --env-file /home/ppzxc/services/overseer/.env -f /opt/services/semaphore/compose.yml stop semaphore
   unset SEMAPHORE_ACCESS_KEY_ENCRYPTION
   ```

3. 데이터 복사 도중에는 SQLite 파일에 접근하는 Semaphore를 중지 상태로 유지합니다. 연결 DSN을 현재 PostgreSQL 주소로 설정하고 도구를 실행합니다. 보고서 경로는 보호된 백업 디렉터리를 사용합니다.

   ```bash
   read -rsp 'PostgreSQL DSN: ' SEMAPHORE_PG_DSN; echo
   export SEMAPHORE_PG_DSN
   /tmp/semaphore-migration-venv/bin/python scripts/migrate-semaphore-postgres-to-sqlite.py \
     --sqlite /data/semaphore/data/database.sqlite \
     --report "$BACKUP_DIR/semaphore-migration-report.json"
   unset SEMAPHORE_PG_DSN
   ```

도구는 PostgreSQL과 SQLite의 애플리케이션 테이블/컬럼/지원 타입 구성이 다르면 즉시 중단합니다. PostgreSQL의 `migration`/`migrations` 테이블은 가져오지 않고, 대상 SQLite가 만든 마이그레이션 이력을 보존합니다. 그 외 테이블 전체를 트랜잭션으로 재복사하고 행 수 및 정규화 SHA-256을 비교합니다. 외래 키, SQLite 무결성, 자동 증가 시퀀스도 검사합니다. 재실행하면 사용자 테이블을 트랜잭션 안에서 비우고 PostgreSQL 스냅샷 데이터를 다시 가져오므로 매 실행마다 새로운 보고서 파일 경로를 지정합니다.

`task__output`을 포함한 모든 애플리케이션 테이블이 대상입니다. 타입, 컬럼, 인코딩, 외래 키 또는 체크섬 검증 중 하나라도 실패하면 컷오버하지 않습니다. PostgreSQL이 변경되지 않았으므로 기존 Semaphore 구성으로 되돌립니다.

## 컷오버 및 검증

1. JSON 보고서에서 모든 테이블의 행 수와 SHA-256이 기록됐는지, `task__output`이 포함됐는지 확인합니다. `sqlite_integrity_check`는 `ok`, `sqlite_foreign_key_violations`는 `0`이어야 합니다.
2. 새 Semaphore를 시작하고 다음을 UI/API에서 확인합니다.
   - 로그인 및 기존 관리자/사용자 계정
   - 프로젝트, 템플릿, 인벤토리, 저장소, 키스토어 조회 및 키스토어 암호 해독
   - 최신/과거 작업 이력과 과거 출력 열람
   - 예약 작업 설정 및 실행 가능 여부
3. 신규 작업 1건을 실행하고 성공 여부, 작업 이력/출력이 SQLite DB에 기록되는지 확인합니다.
4. Boundary 컨테이너가 중지되고 Compose 서비스 목록에서 제외됐는지 확인합니다. `make status`는 OpenBao와 Semaphore만 표시해야 합니다.
5. 검증 후 OpenBao와 Semaphore는 각 서비스 Compose 파일로 관리합니다. PostgreSQL/Boundary 컨테이너 정리는 별도 운영 변경으로 진행하며 `/data/postgres`, custom dump, 설정 백업은 보존 기간 동안 유지합니다.

기존 PostgreSQL과 원본 Semaphore를 정리하기 전에 활성 템플릿별로 SQLite에 신규 작업 기록이 생기는지 확인합니다. 서버 변경 작업은 사전에 허용된 호스트 범위로 제한하고, Host Provisioning은 인벤토리의 `provision_allowed`와 `provision_excluded` 검증을 유지합니다. 메일 재발송처럼 외부에 메시지를 보내는 템플릿은 실제 재발송이 승인되지 않으면 건너뜁니다. 작업 실패가 있으면 원인을 해결하고 해당 템플릿을 재검증한 뒤 정리 단계로 진행합니다.

### 2026-11-13 SQLite 작업 검증 기록

각 활성 템플릿의 최근 실행 결과입니다. Host Audit 재발송은 보관 보고서 조회와 무결성 확인까지 실행하고 이메일 발송은 껐습니다. Provisioning은 기존 성공 이력과 `setup_complete`에 함께 있는 다섯 호스트만 대상으로 했고, 실행 뒤 `provision_allowed`가 빈 상태임을 확인했습니다.

| 템플릿 ID | 작업 ID | 범위 | 결과 |
|---:|---:|---|---|
| 1 | 668 | Cisco 스위치 백업 | 성공 |
| 2 | 671 | `ns0217`, `ns0270`, `ns0325`, `ns0327`, `ns0338` 프로비저닝 | 성공 |
| 3 | 663 | `ns0438` Host Agents 배포 | 성공 |
| 4 | 664 | `ns0438` Host Agents 설정 | 성공 |
| 5 | 662 | `ns0266` 저장소 유지관리 | 성공 |
| 6 | 666 | `ns0438` 월간 Host Audit, 메일 비활성 | 성공 |
| 7 | 657 | 전체 36대 Host Audit | 성공 |
| 8 | 672 | 작업 666 보고서 재발송 검증, 메일 비활성 | 성공 |
| 9 | 665 | `ns0266` Restic 에이전트 배포 | 성공 |
| 10 | 661 | OpenObserve 설정 | 성공 |
| 11 | 669 | FortiGate 설정 백업 | 성공 |
| 12 | 658 | GitHub Webhook Watch | 성공 |

초기 실행에서 확인한 Semaphore Ansible 환경의 `hvac` 누락과 `/var/backups` 쓰기 권한 문제를 수정하고 템플릿 1과 11을 재실행했습니다. 기동 중 `.env`의 암호화 키가 비어 있고 Compose 기본값도 유효한 Base64가 아니어서 기존 키를 복구해 운영 `.env`에 보존했습니다. Compose는 키가 설정되지 않으면 시작을 거부하도록 바꿨습니다. SQLite `PRAGMA integrity_check` 결과는 `ok`였고, 실행 후 `task` 672행과 `task__output` 604,501행이 기록되어 있습니다. PostgreSQL custom dump의 SHA-256 검증과 격리 PostgreSQL 15 컨테이너 복원을 마쳤으며, 복원된 `public` 스키마에 46개 테이블이 확인됐습니다. 원본 PostgreSQL 데이터 디렉터리 `/data/postgres`와 기존 Compose 백업은 유지 중입니다.

## 롤백

검증 하나라도 실패하면 신규 Semaphore를 중지하고 SQLite를 변경 없이 보존합니다. 기존 운영 Compose 파일, override, `.env`를 복구하고 기존 PostgreSQL을 원래 데이터 디렉터리로 시작한 뒤 Semaphore를 PostgreSQL 설정으로 복원합니다. dump 복원이 필요한 경우에는 기존 DB를 덮어쓰지 말고 분리된 DB에 복원한 다음 데이터와 서비스 상태를 확인합니다. 기존 PostgreSQL 컨테이너나 `/data/postgres`를 정리하지 않습니다.

## 완료 기준

- [ ] PostgreSQL custom dump의 체크섬 확인, 목록 확인 및 격리 DB 복원 성공
- [ ] `/data/postgres` 원본과 기존 Compose/`.env` 복구본 보존
- [ ] 모든 애플리케이션 테이블과 `task__output` 행 수/정규화 체크섬 일치
- [ ] SQLite integrity 및 foreign key 검사 통과
- [ ] 로그인, 키스토어 복호화, 객체 조회, 과거 출력, 신규 작업 기록 확인
- [ ] 활성 작업 템플릿의 SQLite 작업 기록 확인 및 실패 원인 해결 (외부 메시지 발송은 별도 승인 필요)
- [ ] Boundary 제외, OpenBao 및 Semaphore 상태 점검 통과
- [ ] 보존 기간을 정하고, 기간 만료 후 별도 변경 승인 전까지 PostgreSQL 데이터 삭제 금지
