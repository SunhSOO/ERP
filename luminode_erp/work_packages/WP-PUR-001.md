# WP-PUR-001 — 공급사·구매요청·견적비교

- Phase: 3 (결재·구매·재무·자산)
- 실행 파동: 3.2
- Stream: `operations`
- 주 담당 역할: Operations Domain Agent
- 위험도: `high`
- 상태: `proposed`
- 선행 작업: `WP-APR-002`, `WP-CRM-001`

## 목표

구매 목적, 예산, 후보 공급사와 비교견적을 관리한다.

## 소유 모듈

- `procurement`

## 산출물

- supplier extension
- purchase request
- quote comparison

## 수용 기준

- 승인 전 발주가 불가하다
- 요청 금액 변경 시 재결재한다
- 공급사 민감정보 접근이 제한된다

## 필수 리뷰

- `architecture`
- `qa_security`

## 시작 계약

```text
Work Package: WP-PUR-001
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

