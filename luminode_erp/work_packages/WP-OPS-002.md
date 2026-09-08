# WP-OPS-002 — 관측성·백업 최소구성

- Phase: 0 (기반 플랫폼)
- 실행 파동: 0.8
- Stream: `infra`
- 주 담당 역할: DevOps Agent
- 위험도: `critical`
- 상태: `proposed`
- 선행 작업: `WP-OPS-001`, `WP-PLT-005`, `WP-PLT-006`

## 목표

로그·메트릭·경보와 PostgreSQL/MinIO 백업을 구성한다.

## 소유 모듈

- `operations`

## 산출물

- Prometheus/Grafana/Loki
- backup jobs
- restore runbook

## 수용 기준

- 핵심 서비스 상태가 보인다
- 백업 실패 경보가 발생한다
- 샘플 복원과 파일 체크섬 검증이 완료된다

## 필수 리뷰

- `architecture`
- `qa_security`

## 시작 계약

```text
Work Package: WP-OPS-002
Base Commit:
Owner:
In Scope:
Out of Scope:
Owned Paths:
Owned Tables:
API Contracts:
Events:
Permissions:
State Transitions:
Migration Plan:
Tests:
Shared Files Needed:
Risks and Assumptions:
```

## 완료 증거

- [ ] 구현 commit/MR
- [ ] 테스트 명령과 결과
- [ ] migration 및 forward-fix/rollback 설명
- [ ] API·이벤트·권한 문서
- [ ] 보안·개인정보 검토
- [ ] 운영·사용자 문서
- [ ] 독립 리뷰
- [ ] 기본 브랜치 통합 CI


Phase 0 상세 절차는 `15_PHASE_0_FOUNDATION_IMPLEMENTATION_PLAN.md`의 `WP-OPS-002` 절을 따른다.
