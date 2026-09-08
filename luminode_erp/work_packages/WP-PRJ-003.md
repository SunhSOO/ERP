# WP-PRJ-003 — 업무·하위업무·의존성

- Phase: 1 (프로젝트 운영 코어)
- 실행 파동: 1.2
- Stream: `project`
- 주 담당 역할: Project Domain Agent
- 위험도: `high`
- 상태: `proposed`
- 선행 작업: `WP-PRJ-001`, `WP-UI-001`

## 목표

업무 상태, 담당, 체크리스트, 의존성, 칸반을 구현한다.

## 소유 모듈

- `project`

## 산출물

- task APIs
- kanban/list views
- dependency validation

## 수용 기준

- 순환 의존성을 차단한다
- 동시 수정 충돌을 처리한다
- 다른 프로젝트 업무 접근을 차단한다

## 필수 리뷰

- `architecture`
- `qa_security`

## 시작 계약

```text
Work Package: WP-PRJ-003
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

