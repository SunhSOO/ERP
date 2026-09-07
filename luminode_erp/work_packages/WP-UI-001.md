# WP-UI-001 — 디자인 시스템·전역 레이아웃

- Phase: 0 (기반 플랫폼)
- 실행 파동: 0.4
- Stream: `ux`
- 주 담당 역할: Frontend/UX Agent
- 위험도: `medium`
- 상태: `proposed`
- 선행 작업: `WP-PLT-001`, `WP-PLT-002`

## 목표

공통 컴포넌트, 내비게이션, 화면 상태 표준을 만든다.

## 소유 모듈

- `frontend-core`

## 산출물

- design tokens
- app shell
- shared components

## 수용 기준

- loading/empty/error/forbidden/stale 패턴이 제공된다
- 키보드와 반응형 기본 검증을 통과한다
- 권한 기반 메뉴가 동작한다

## 필수 리뷰

- `domain_owner`
- `qa`

## 시작 계약

```text
Work Package: WP-UI-001
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


Phase 0 상세 절차는 `15_PHASE_0_FOUNDATION_IMPLEMENTATION_PLAN.md`의 `WP-UI-001` 절을 따른다.
