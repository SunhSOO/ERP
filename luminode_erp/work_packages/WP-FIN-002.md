# WP-FIN-002 — 매출·수금·매입·지급 상태

- Phase: 3 (결재·구매·재무·자산)
- 실행 파동: 3.4
- Stream: `operations`
- 주 담당 역할: Operations Domain Agent
- 위험도: `critical`
- 상태: `proposed`
- 선행 작업: `WP-CON-002`, `WP-FIN-001`, `WP-PUR-002`

## 목표

계약 지급 일정과 실제 청구/수금/지급 기록을 연결한다.

## 소유 모듈

- `finance`

## 산출물

- revenue/payable ledgers
- collection/payment records
- overdue alerts

## 수용 기준

- 계획과 실제를 구분한다
- 부분 수금이 정확하다
- 취소/정정 이력을 삭제하지 않는다

## 필수 리뷰

- `architecture`
- `qa_security`

## 시작 계약

```text
Work Package: WP-FIN-002
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

