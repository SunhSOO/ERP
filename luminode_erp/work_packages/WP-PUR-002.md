# WP-PUR-002 — 발주·부분입고·검수·반품

- Phase: 3 (결재·구매·재무·자산)
- 실행 파동: 3.3
- Stream: `operations`
- 주 담당 역할: Operations Domain Agent
- 위험도: `critical`
- 상태: `proposed`
- 선행 작업: `WP-PUR-001`, `WP-DMS-001`

## 목표

발주서와 입고 원장을 구현한다.

## 소유 모듈

- `procurement`

## 산출물

- purchase order
- goods receipt
- return flow

## 수용 기준

- 부분 입고 수량이 정확하다
- 발주 초과 입고를 통제한다
- 입고/반품 이력이 불변으로 남는다

## 필수 리뷰

- `architecture`
- `qa_security`

## 시작 계약

```text
Work Package: WP-PUR-002
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

