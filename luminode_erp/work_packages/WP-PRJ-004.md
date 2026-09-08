# WP-PRJ-004 — 리스크·이슈·의사결정

- Phase: 1 (프로젝트 운영 코어)
- 실행 파동: 1.2
- Stream: `project`
- 주 담당 역할: Project Domain Agent
- 위험도: `medium`
- 상태: `proposed`
- 선행 작업: `WP-PRJ-001`, `WP-PLT-007`

## 목표

프로젝트 위험과 문제, 결정 근거를 추적한다.

## 소유 모듈

- `project`

## 산출물

- risk/issue/decision APIs
- register screens
- escalation events

## 수용 기준

- 리스크와 이슈 상태가 구분된다
- 결정 대체 관계를 보존한다
- 고위험 리스크 알림이 동작한다

## 필수 리뷰

- `domain_owner`
- `qa`

## 시작 계약

```text
Work Package: WP-PRJ-004
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

