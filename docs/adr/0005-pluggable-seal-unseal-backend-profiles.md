# ADR 0005: Pluggable Seal/Unseal Backend Profiles for OpenBao & Boundary

## 1. Context & Background (배경)
Overseer는 소-중규모 온프레미스 IDC 인프라를 위한 Docker Compose 기반 중앙 컨트롤 플레인입니다.
기본 환경에서는 완전한 독립 구동을 위해 OpenBao Shamir 키 방식 및 Boundary 로컬 AEAD 환경변수 암호화 키 방식을 사용합니다.
그러나 엔터프라이즈 환경 및 하이브리드 클라우드 연동 요구사항에 따라 GCP Cloud KMS를 활용한 **자동 언실(Auto-Unseal)** 및 하드웨어 보안 수준의 KMS 키 관리 요구가 발생하였습니다.

## 2. Decision (결정 사항)

1. **프로파일 기반 설정 모듈화 (`profiles/`)**:
   - `openbao/config/profiles/` 아래에 `local-shamir.hcl`, `gcp-kms.hcl` 프로파일 정의
   - `boundary/config/profiles/` 아래에 `local-aead.hcl`, `gcp-kms.hcl` (controller 및 worker) 정의
   - `SEAL_TYPE`(`local` 또는 `gcpkms`)에 따라 활성 설정(`openbao.hcl`, `controller.hcl`, `worker.hcl`)으로 자동 주입/적용

2. **3가지 통합 마스터 키 관리 프로파일 (`KEY_MANAGEMENT_PROFILE`)**:
   - `[1] Local .env Persisted` (`local`): OpenBao Shamir 키 파일 디스크 보관, Boundary AEAD 키 및 Semaphore 암호화 키를 `.env`에 저장하여 호스트 재부팅 시 완전 자동 복구/언실 지원.
   - `[2] Zero-Knowledge Manual` (`manual`): 모든 마스터 키(OpenBao Shamir, Boundary AEAD 3종, Semaphore 암호화 키)를 터미널에 1회 백업 출력 후 `.env` 및 디스크에서 **완전 삭제(Zero-Knowledge Wipe)**. 재부팅 시 환경변수 주입(`export KEY=...`) 또는 `orchestrator.ensure_runtime_keys_injected`를 통한 대화형 런타임 메모리 주입 지원.
   - `[3] External Cloud KMS` (`gcpkms`): Google Cloud KMS HSM을 통해 OpenBao 및 Boundary 마스터 키를 암호화/자동 언실하며 호스트에 로컬 키를 저장하지 않음.

3. **OpenBao 초기화 스크립트 분기 (`init-openbao-ssh-ca.sh`)**:
   - `SEAL_TYPE=local`: `bao operator init` -> Shamir unseal 키 저장 및 수동 Unseal API 호출
   - `SEAL_TYPE=gcpkms`: `bao operator init` -> GCP KMS Auto-Unseal 동작에 따른 Recovery Keys 보관 및 자동 언실 상태 확인

4. **포괄적인 컨테이너 기반 통합 테스트 작성**:
   - `tests/test_06_seal_matrix.py`를 통해 모든 설정 매트릭스(Local Shamir, Local AEAD, Zero-Knowledge Wipe, GCP Cloud KMS 프로파일 유효성, HCL 파싱, 컨테이너 환경변수 바인딩, Orchestrator 분기 로직, 재부팅 런타임 키 주입 인터페이스)를 검증

## 3. Status & Consequences (상태 및 영향)
- **Status**: Accepted
- **Consequences**:
  - IDC 온프레미스 단독 환경과 GCP KMS 연동 하이브리드 환경을 코드 수정 없이 `make bootstrap`과 `.env` 설정만으로 손쉽게 전환 가능
  - 디스크에 암호화 키를 일절 남기지 않는 Zero-Knowledge 환경 운영 시에도 터미널 백업 및 재부팅 시 런타임 세션 주입을 통해 완벽한 보안성과 운영 연속성 확보
  - 향후 AWS KMS, Azure Key Vault, HashiCorp Vault Transit 등 추가 KMS 백엔드 확장이 용이해짐
