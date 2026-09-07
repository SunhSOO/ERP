# WP-HR-003 — 휴가 부여·잔여·신청

- Phase: 4 (인사·근태·휴가)
- 실행 파동: 4.2
- Stream: `people`
- 주 담당 역할: People/HR Domain Agent
- 위험도: `critical`
- 상태: `proposed`
- 선행 작업: `WP-HR-001`, `WP-CAL-001`, `WP-APR-002`

## 목표

휴가 잔액과 팀 일정, 결재를 구현한다.

## 소유 모듈

- `hr`

## 산출물

- leave ledger
- request flow
- team calendar

## 수용 기준

- 잔액 동시 차감이 안전하다
- 반일/시간 단위를 처리한다
- 승인/취소 후 잔액이 일치한다

## 필수 리뷰

- `architecture`
- `qa_security`

## 시작 계약

```text
Work Package: WP-HR-003
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

