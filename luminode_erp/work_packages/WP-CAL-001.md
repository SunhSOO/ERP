# WP-CAL-001 — 캘린더·회의·회의록 수동 기능

- Phase: 1 (프로젝트 운영 코어)
- 실행 파동: 1.2
- Stream: `project`
- 주 담당 역할: Project Domain Agent
- 위험도: `medium`
- 상태: `proposed`
- 선행 작업: `WP-PRJ-001`, `WP-PLT-007`

## 목표

개인/프로젝트 일정과 회의 안건, 결정, 액션을 관리한다.

## 소유 모듈

- `calendar`
- `meeting`

## 산출물

- calendar APIs
- meeting screens
- action item model

## 수용 기준

- 회의와 프로젝트가 연결된다
- 참석/안건/결정/액션을 기록한다
- 액션을 수동 업무로 전환한다

## 필수 리뷰

- `domain_owner`
- `qa`

## 시작 계약

```text
Work Package: WP-CAL-001
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

