# 4. Centralized /data Directory Layout and Automated Secret Keygen on Bootstrap

- **Status**: Accepted
- **Date**: 2026-09-02
- **Deciders**: Overseer Engineering Team & User
- **Context**: IDC On-Premise Storage Consolidation & Zero-Trust Secret Key Bootstrap

---

## 1. Context & Problem Statement (배경 및 문제 정의)

1. **가변 대용량 데이터 파편화**:
   - 기존 Docker Named Volume(`postgres-data`, `semaphore-data`)과 로컬 상대 경로(`./openbao/data`)가 혼재되어 백업, 디스크 용량 모니터링, 고속 스토리지(SSD/NVMe) 마운트 제어가 파편화됨.
   - IDC 환경의 대용량/고속 전용 파티션(`/data`)에 모든 서비스의 영구 데이터를 일원화하여 관리할 필요성 대두 (ADR-0002 FHS 표준과 연계).

2. **초기 프로비저닝 시 정적 키 노출 위험**:
   - `.env.example`에 정의된 Boundary AEAD KMS 키, Semaphore 암호화 키, 데이터베이스 패스워드 등이 `make bootstrap` 실행 시 단순 복사되어 초기화될 경우 보안 취약점이 발생할 수 있음.
   - 수동으로 여러 개의 32바이트 Base64 키를 생성(`openssl rand -base64 32`)하고 입력하는 과정은 번거롭고 인적 오류를 유발함.

---

## 2. Decision Outcomes (결정 사항)

### 2.1 `/data/{SERVICE_NAME}` 중앙 데이터 레이아웃 표준화
모든 컨트롤 플레인 서비스의 영구 데이터 디렉터리를 `DATA_DIR`(기본값 `/data`) 하위의 표준 서비스 디렉터리로 바인드 마운트합니다.

| 서비스 | 호스트 저장 경로 | 컨테이너 마운트 경로 | 데이터 설명 |
|---|---|---|---|
| **PostgreSQL** | `${DATA_DIR}/postgres` | `/var/lib/postgresql/data` | Boundary 및 Semaphore RDBMS 영구 데이터 |
| **OpenBao** | `${DATA_DIR}/openbao` | `/openbao/data` | Raft 스토리지 데이터, SSH CA 공개키, Unseal 정보 |
| **Semaphore UI** | `${DATA_DIR}/semaphore` | `/tmp/semaphore` | GitOps 저장소 캐시, 작업 실행 로그, 임시 키스토어 |
| **Boundary** | `${DATA_DIR}/boundary` | `/boundary/data` | Controller/Worker 로컬 세션 및 감사 캐시 데이터 |

### 2.2 `make bootstrap` 시 암호화 키 및 비밀번호 자동 생성 (Keygen)
`scripts/orchestrator.py`의 `ensure_env_file()` 단계에서 `.env` 파일이 존재하지 않는 경우, `.env.example`을 템플릿으로 사용하여 다음 암호학적 난수 키를 동적으로 자동 생성합니다:

1. **Boundary KMS AEAD Key 3종** (32-byte Base64):
   - `BOUNDARY_KMS_AEAD_ROOT_KEY`
   - `BOUNDARY_KMS_AEAD_WORKER_AUTH_KEY`
   - `BOUNDARY_KMS_AEAD_RECOVERY_KEY`
2. **Semaphore Access Key Encryption Key** (32-byte Base64):
   - `SEMAPHORE_ACCESS_KEY_ENCRYPTION`
3. **무작위 데이터베이스 및 관리자 비밀번호**:
   - `POSTGRES_PASSWORD` (16-byte 안전한 영숫자 문자열)
   - `SEMAPHORE_ADMIN_PASSWORD` (16-byte 안전한 영숫자 문자열)
4. **`DATA_DIR` 기본값 설정**:
   - `DATA_DIR=/data`

---

## 3. Benefits & Consequences (효과 및 운영 영향)

- **백업 및 스토리지 통합**: 단일 `/data` 디렉터리 백업 및 스냅샷만으로 모든 상태 저장소(PostgreSQL, OpenBao Raft, Semaphore)의 일괄 백업/복구 가능.
- **Zero-Trust 보안성 강화**: 배포 시마다 고유한 32바이트 KMS 암호화 키와 무작위 패스워드가 자동 주입되어 기본값 유출 위험 원천 차단.
- **개발 환경 유연성**: 로컬 개발 환경이나 비루트 테스트 환경에서는 `.env`에 `DATA_DIR=./data`로 오버라이드하여 간편하게 테스트 가능.
