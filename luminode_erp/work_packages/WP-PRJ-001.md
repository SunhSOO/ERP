# WP-PRJ-001 — 프로젝트·멤버·상태

- Phase: 1 (프로젝트 운영 코어)
- 실행 파동: 1.1
- Stream: `project`
- 주 담당 역할: Project Domain Agent
- 위험도: `high`
- 상태: `proposed`
- 선행 작업: `WP-QA-000`

## 목표

프로젝트 기본 정보, 참여자, 상태 머신을 구현한다.

## 소유 모듈

- `project`

## 산출물

- project APIs
- project permissions
- project screens

## 수용 기준

- 프로젝트 코드가 중복되지 않는다
- 프로젝트 범위 권한이 적용된다
- 상태 전이가 감사된다

## 필수 리뷰

- `architecture`
- `qa_security`

## 시작 계약

```text
Work Package: WP-PRJ-001
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

