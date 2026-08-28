# Overseer Testing & Traceability Documentation Index

Overseer 컨트롤 플레인의 전체 테스트 프레임워크, 3단 정합성 검증 및 가이드라인 문서 모음입니다.

---

## 1. 테스트 계층 및 문서 안내

| 문서 | 대상 계층 | 핵심 도구 | 설명 |
|---|---|---|---|
| 📑 [3-Way Traceability Matrix](file:///home/ppzxc/projects/overseer/docs/tests/TRACEABILITY_MATRIX.md) | **전역 정합성** | `validate-specs.py` | 문서 ⟷ 코드 ⟷ 테스트 3단 100% 추적 매트릭스 리포트 (자동 생성) |
| 🧪 [E2E 시스템 통합 테스트 가이드](file:///home/ppzxc/projects/overseer/docs/tests/E2E_TESTING_GUIDELINE.md) | **Full-Stack 시스템** | `pytest`, `requests` | OpenBao, Boundary, Semaphore UI, PostgreSQL 전체 컨트롤 플레인 E2E 검증 |

---

## 2. 테스트 원클릭 실행 요약

```bash
# 1. 3단 정합성 검증 (스펙 문서 <-> 코드 <-> 테스트)
make spec-check

# 2. Control Plane E2E 시스템 통합 테스트 (Pytest)
make test-e2e
```
