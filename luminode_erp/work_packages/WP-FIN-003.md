# WP-FIN-003 — 프로젝트 손익·스냅샷

- Phase: 3 (결재·구매·재무·자산)
- 실행 파동: 3.5
- Stream: `operations`
- 주 담당 역할: Operations Domain Agent
- 위험도: `high`
- 상태: `proposed`
- 선행 작업: `WP-FIN-001`, `WP-FIN-002`

## 목표

계약/매출/비용/예산의 근거 있는 프로젝트 손익을 제공한다.

## 소유 모듈

- `finance`
- `analytics`

## 산출물

- profitability service
- daily snapshots
- dashboard

## 수용 기준

- 모든 수치가 원장으로 드릴다운된다
- 예상/확정 손익이 구분된다
- 기준일과 포함 범위가 표시된다

## 필수 리뷰

- `architecture`
- `qa_security`

## 시작 계약

```text
Work Package: WP-FIN-003
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

