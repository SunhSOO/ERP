# WP-INV-001 — 소모품 재고 원장

- Phase: 3 (결재·구매·재무·자산)
- 실행 파동: 3.4
- Stream: `operations`
- 주 담당 역할: Operations Domain Agent
- 위험도: `critical`
- 상태: `proposed`
- 선행 작업: `WP-PUR-002`

## 목표

위치별 입출고/이동/조정과 안전재고를 관리한다.

## 소유 모듈

- `inventory`

## 산출물

- inventory ledger
- balance locking
- stock alerts

## 수용 기준

- 음수 재고를 방지한다
- 조정 사유와 승인이 남는다
- 원장과 잔액 재계산이 일치한다

## 필수 리뷰

- `architecture`
- `qa_security`

## 시작 계약

```text
Work Package: WP-INV-001
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

