# WP-QA-P3 — Phase 3 운영·재무 게이트

- Phase: 3 (결재·구매·재무·자산)
- 실행 파동: 3.6
- Stream: `qa`
- 주 담당 역할: QA·Security Agent
- 위험도: `critical`
- 상태: `proposed`
- 선행 작업: `WP-FIN-003`, `WP-AUT-002`, `WP-INT-ACC-001`

## 목표

구매·비용·자산·손익의 E2E와 금액 무결성을 검증한다.

## 소유 모듈

- `qa`

## 산출물

- procure-to-asset E2E
- expense E2E
- ledger reconciliation

## 수용 기준

- 금액/수량 원장이 일치한다
- 프로젝트 손익을 원본으로 추적한다
- 승인/권한 우회가 없다

## 필수 리뷰

- `architecture`
- `qa_security`

## 시작 계약

```text
Work Package: WP-QA-P3
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

