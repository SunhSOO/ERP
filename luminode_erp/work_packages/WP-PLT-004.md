# WP-PLT-004 — RBAC·범위 권한 엔진

- Phase: 0 (기반 플랫폼)
- 실행 파동: 0.5
- Stream: `platform`
- 주 담당 역할: Platform Backend Agent
- 위험도: `critical`
- 상태: `proposed`
- 선행 작업: `WP-PLT-002`, `WP-PLT-003`

## 목표

기능 권한과 company/department/project/self 범위를 판정한다.

## 소유 모듈

- `iam`

## 산출물

- permission catalog
- policy engine
- permission simulator

## 수용 기준

- object-level 권한이 API마다 적용된다
- 외부 사용자는 초대 프로젝트만 접근한다
- 권한 변경이 감사된다

## 필수 리뷰

- `architecture`
- `qa_security`

## 시작 계약

```text
Work Package: WP-PLT-004
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


Phase 0 상세 절차는 `15_PHASE_0_FOUNDATION_IMPLEMENTATION_PLAN.md`의 `WP-PLT-004` 절을 따른다.
