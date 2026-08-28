# Control Plane E2E 시스템 통합 테스트 가이드라인 (Pytest)

본 문서는 **Overseer**의 중앙 컨트롤 플레인(OpenBao, Boundary, Semaphore UI, PostgreSQL)이 유기적으로 연결되어 동작하는지 검증하는 **E2E 시스템 통합 테스트 스위트(`tests/`)**의 구조와 실행 가이드를 정의합니다.

---

## 1. E2E 테스트 아키텍처

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                      Pytest E2E System Integration Suite                    │
│                                                                             │
│  [test_00_spec_traceability.py] ───> 전역 3단 정합성 검증 (validate-specs)  │
│  [test_01_control_plane.py]     ───> Postgres, OpenBao, Boundary, Semaphore │
│  [test_02_openbao_ssh_ca.py]    ───> OpenBao SSH CA 키 생성 & 인증서 서명  │
│  [test_03_boundary.py]          ───> Boundary Controller & Worker 프록시   │
│  [test_04_ansible_e2e.py]       ───> Semaphore GitOps & Volume 정합성 검증 │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. 테스트 스위트 상세 구성

| 테스트 파일 | 주요 검증 항목 |
|---|---|
| `test_00_spec_traceability.py` | 모든 컨트롤 플레인 스펙 문서, 구현 코드, 자동화 테스트 간의 **3-Way 정합성 100% 검증** |
| `test_01_control_plane.py` | PostgreSQL(5432), OpenBao(8200), Boundary(9200), Semaphore UI(3000) 포트 및 HTTP 헬스체크 |
| `test_02_openbao_ssh_ca.py` | OpenBao Unseal 상태, SSH CA 공개키 생성 및 **실시간 SSH User Certificate 서명 발급** |
| `test_03_boundary.py` | Boundary Controller 클러스터 포트(9201) 및 Worker 프록시 포트(9202) 정상 리스닝 |
| `test_04_ansible_e2e.py` | Semaphore UI의 GitOps 원격 레포지토리 연동 및 환경 구성 검증 |

---

## 3. 실행 방법

```bash
cd /home/ppzxc/projects/overseer

# E2E 전체 테스트 실행
make test-e2e

# 특정 테스트 모듈만 실행
pytest tests/test_01_control_plane.py -v
```
