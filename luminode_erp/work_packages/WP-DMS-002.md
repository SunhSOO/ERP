# WP-DMS-002 — 산출물·검토·제출

- Phase: 1 (프로젝트 운영 코어)
- 실행 파동: 1.3
- Stream: `document`
- 주 담당 역할: DMS Agent
- 위험도: `critical`
- 상태: `proposed`
- 선행 작업: `WP-DMS-001`, `WP-PRJ-002`

## 목표

필수 산출물, 검토, 승인, 제출 이력을 구현한다.

## 소유 모듈

- `dms`
- `project`

## 산출물

- deliverable APIs
- review flow
- submission records

## 수용 기준

- 필수 산출물 상태를 추적한다
- 승인/제출본을 잠근다
- 면제에는 결재 근거가 필요하다

## 필수 리뷰

- `architecture`
- `qa_security`

## 시작 계약

```text
Work Package: WP-DMS-002
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

