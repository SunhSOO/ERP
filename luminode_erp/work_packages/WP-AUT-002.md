# WP-AUT-002 — 입고→자산/재고 반영

- Phase: 3 (결재·구매·재무·자산)
- 실행 파동: 3.5
- Stream: `operations`
- 주 담당 역할: Operations Domain Agent
- 위험도: `high`
- 상태: `proposed`
- 선행 작업: `WP-PUR-002`, `WP-AST-001`, `WP-INV-001`

## 목표

입고 품목을 자산 초안 또는 재고로 안전하게 변환한다.

## 소유 모듈

- `procurement`
- `asset`
- `inventory`

## 산출물

- conversion preview
- bulk asset draft
- idempotent workflow

## 수용 기준

- 동일 입고의 중복 자산이 없다
- 시리얼 미입력 항목을 명확히 표시한다
- 부분 실패를 재처리한다

## 필수 리뷰

- `architecture`
- `qa_security`

## 시작 계약

```text
Work Package: WP-AUT-002
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

