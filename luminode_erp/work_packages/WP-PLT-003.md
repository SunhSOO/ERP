# WP-PLT-003 — 회사·부서·직원·사용자 관리

- Phase: 0 (기반 플랫폼)
- 실행 파동: 0.4
- Stream: `platform`
- 주 담당 역할: Platform Backend Agent
- 위험도: `high`
- 상태: `proposed`
- 선행 작업: `WP-PLT-002`

## 목표

조직과 계정의 기준 엔터티 및 관리자 화면 계약을 만든다.

## 소유 모듈

- `iam`
- `hr-core`

## 산출물

- organization APIs
- employee/user models
- admin screens

## 수용 기준

- 부서 계층과 직원 소속을 관리한다
- 사용자와 직원 연결/분리가 가능하다
- 퇴사 이력을 삭제하지 않는다

## 필수 리뷰

- `architecture`
- `qa_security`

## 시작 계약

```text
Work Package: WP-PLT-003
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


Phase 0 상세 절차는 `15_PHASE_0_FOUNDATION_IMPLEMENTATION_PLAN.md`의 `WP-PLT-003` 절을 따른다.
