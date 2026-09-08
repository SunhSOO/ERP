# WP-AUT-003 — 퇴사·인계·회수 워크플로우

- Phase: 4 (인사·근태·휴가)
- 실행 파동: 4.2
- Stream: `people`
- 주 담당 역할: People/HR Domain Agent
- 위험도: `critical`
- 상태: `proposed`
- 선행 작업: `WP-HR-001`, `WP-AST-001`, `WP-PLT-002`, `WP-PRJ-003`

## 목표

퇴사 시 계정, 자산, 업무, 외부 공유를 회수한다.

## 소유 모듈

- `hr`
- `iam`
- `asset`
- `project`

## 산출물

- offboarding checklist
- revocation workflow
- handover report

## 수용 기준

- 세션/토큰이 즉시 철회된다
- 자산과 미완료 업무가 누락 없이 표시된다
- 작성 이력은 보존된다

## 필수 리뷰

- `architecture`
- `qa_security`

## 시작 계약

```text
Work Package: WP-AUT-003
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

