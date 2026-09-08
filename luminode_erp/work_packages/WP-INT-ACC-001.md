# WP-INT-ACC-001 — 외부 회계 내보내기

- Phase: 3 (결재·구매·재무·자산)
- 실행 파동: 3.5
- Stream: `integration`
- 주 담당 역할: Integration Agent
- 위험도: `critical`
- 상태: `proposed`
- 선행 작업: `WP-FIN-002`

## 목표

승인된 비용/매출/매입을 외부 회계 형식으로 내보낸다.

## 소유 모듈

- `integration`
- `finance`

## 산출물

- export mappings
- batch status
- error report

## 수용 기준

- 내보낸 항목을 중복 전송하지 않는다
- 오류 항목을 재처리한다
- 외부 ID와 상태를 추적한다

## 필수 리뷰

- `architecture`
- `qa_security`

## 시작 계약

```text
Work Package: WP-INT-ACC-001
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

