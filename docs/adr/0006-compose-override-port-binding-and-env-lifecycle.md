# ADR 0006: Modular 1:1 Host Port Binding via compose.override.yml and Lazy .env Variable Lifecycle

- **Status**: Accepted
- **Date**: 2026-09-02
- **Deciders**: Overseer Engineering Team & User
- **Context**: IDC Network Security, Zero-Trust Host Port Isolation, and Minimal Clean .env Bootstrapping

---

## 1. Context & Background (배경)

1. **호스트 포트 노출 vs 내부망 전용 격리 (Zero-Trust)**:
   - 기본 Compose 파일(`compose.yml`)에 포트 바인딩(`ports:`)이 하드코딩되어 있거나 빈 문자열/더미 매핑이 들어가는 경우, Docker Compose 기동 시 의도치 않게 호스트 포트가 외부에 노출되거나 불필요한 바인딩 충돌이 발생할 수 있습니다.
   - 호스트에 포트를 바인딩할 때는 항상 서비스 포트와 1:1 매핑(`0.0.0.0:<port>:<port>`)을 보장하고, 바인딩하지 않을 때(Internal only)는 Compose에서 `ports` 블록 자체를 제외하여 `backend` Docker 전용 브릿지 네트워크로만 안전하게 통신해야 합니다.

2. **환경변수 템플릿(`.env.example`)의 직관성과 점진적 활성화 (Lazy Lifecycle)**:
   - 초기 부트스트랩 단계에서는 사용되지 않는 조건부 변수(예: `SEAL_TYPE=local`일 때 불필요한 GCP Cloud KMS 변수들, 수동 키 관리 모드 변수들, 비활성화된 포트 매핑 변수들)가 활성화되어 있으면 혼란을 초래합니다.
   - `.env.example` 템플릿에서는 선택적/조건부 변수를 기본 주석(`#`) 처리 상태로 제공하고, `make bootstrap`(`scripts/orchestrator.py`) 실행 시 사용자가 선택한 모드(예: `EXPOSE_PORTS=true`, `SEAL_TYPE=gcpkms`)에 맞춰 필요한 변수의 주석을 해제하고 값을 설정하는 라이프사이클을 도입합니다.

---

## 2. Decision Outcomes (결정 사항)

### 2.1 `compose.override.yml` 기반의 1:1 포트 바인딩 오버라이드
- 기본 `compose.yml`에서는 모든 서비스의 `ports:` 블록을 제거하여 기본 상태를 완전 내부망 전용(Internal only)으로 정의합니다.
- `make bootstrap` 또는 `orchestrator.py` 실행 시 `EXPOSE_PORTS=true`인 경우:
  - `compose.override.yml`을 동적으로 생성하여 `0.0.0.0:<port>:<port>` 1:1 바인딩을 주입합니다.
    - OpenBao: `0.0.0.0:8200:8200`
    - Boundary Controller: `0.0.0.0:9200:9200`, `0.0.0.0:9201:9201`
    - Boundary Worker: `0.0.0.0:9202:9202`
    - Semaphore UI: `0.0.0.0:3000:3000`
- `EXPOSE_PORTS=false` (Internal only)인 경우:
  - `compose.override.yml` 파일을 삭제하여 호스트 포트 바인딩을 원천 차단합니다.

### 2.2 `.env` 점진적 활성화 (Comment / Uncomment Lifecycle)
- `scripts/orchestrator.py`에 `set_env_var(key, value, uncomment)` 로직을 구현하여:
  - `SEAL_TYPE=gcpkms` 선택 시: GCP Cloud KMS 변수(`GCP_PROJECT`, `GCP_REGION`, `GCP_KEY_RING` 등) 주석 해제 및 설정.
  - `SEAL_TYPE=local` 선택 시: GCP Cloud KMS 변수를 주석(`#`) 처리 상태로 유지.
  - `EXPOSE_PORTS=true` 선택 시: 포트 변수 주석 해제 및 `0.0.0.0:<port>:<port>` 설정.
  - `EXPOSE_PORTS=false` 선택 시: 포트 변수를 주석(`#`) 처리하여 `.env` 가독성 및 보안성 확보.

---

## 3. Consequences & Benefits (영향 및 이점)
- **Zero-Trust 네트워크 격리**: 포트 미바인딩 환경에서 호스트 포트 노출 위험이 완전히 차단됩니다.
- **명확한 호스트 바인딩 규격**: 포트 바인딩 활성화 시 `0.0.0.0` 인터페이스에 서비스 포트와 동일한 1:1 매핑이 일관되게 보장됩니다.
- **클린한 설정 파일 관리**: 실제 활성화된 기능에 해당하는 환경변수만 주석이 풀려 있어 운영자가 `.env` 파일의 상태를 한눈에 파악할 수 있습니다.
