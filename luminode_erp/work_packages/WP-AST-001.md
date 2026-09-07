# WP-AST-001 — 자산·대여·점검·폐기

- Phase: 3 (결재·구매·재무·자산)
- 실행 파동: 3.4
- Stream: `operations`
- 주 담당 역할: Operations Domain Agent
- 위험도: `critical`
- 상태: `proposed`
- 선행 작업: `WP-PUR-002`, `WP-APR-002`, `WP-PLT-003`

## 목표

개별 자산의 보유자, 위치, 상태와 이력을 관리한다.

## 소유 모듈

- `asset`

## 산출물

- asset APIs
- assignment/return
- maintenance/disposal

## 수용 기준

- 자산 상태 전이가 검증된다
- 보유자/위치 변경 이력이 남는다
- 폐기에는 승인 근거가 필요하다

## 필수 리뷰

- `architecture`
- `qa_security`

## 시작 계약

```text
Work Package: WP-AST-001
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

