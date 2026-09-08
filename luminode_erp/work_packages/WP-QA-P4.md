# WP-QA-P4 — Phase 4 인사 개인정보 게이트

- Phase: 4 (인사·근태·휴가)
- 실행 파동: 4.3
- Stream: `qa`
- 주 담당 역할: QA·Security Agent
- 위험도: `critical`
- 상태: `proposed`
- 선행 작업: `WP-HR-002`, `WP-HR-003`, `WP-HR-004`, `WP-AUT-003`

## 목표

근태·휴가·퇴사와 민감정보 접근을 검증한다.

## 소유 모듈

- `qa`

## 산출물

- HR permission suite
- leave concurrency tests
- offboarding E2E

## 수용 기준

- 타인 민감정보 노출이 없다
- 휴가 잔액 경쟁조건을 통과한다
- 퇴사 후 접근이 차단된다

## 필수 리뷰

- `architecture`
- `qa_security`

## 시작 계약

```text
Work Package: WP-QA-P4
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

