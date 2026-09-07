# WP-FIN-001 — 비용·증빙·예산

- Phase: 3 (결재·구매·재무·자산)
- 실행 파동: 3.2
- Stream: `operations`
- 주 담당 역할: Operations Domain Agent
- 위험도: `critical`
- 상태: `proposed`
- 선행 작업: `WP-APR-002`, `WP-DMS-001`, `WP-PRJ-001`

## 목표

비용 신청, 항목 배부, 예산 잔액을 구현한다.

## 소유 모듈

- `finance`

## 산출물

- expense APIs
- budget ledger
- receipt checks

## 수용 기준

- 배부 합계가 원금액과 일치한다
- 예산 초과 정책이 적용된다
- 증빙 중복 후보를 표시한다

## 필수 리뷰

- `architecture`
- `qa_security`

## 시작 계약

```text
Work Package: WP-FIN-001
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

