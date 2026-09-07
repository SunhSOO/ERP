# WP-PLT-002 — 인증·세션·MFA 기반

- Phase: 0 (기반 플랫폼)
- 실행 파동: 0.3
- Stream: `platform`
- 주 담당 역할: Platform Backend Agent
- 위험도: `critical`
- 상태: `proposed`
- 선행 작업: `WP-PLT-001`, `WP-OPS-001`

## 목표

사용자 로그인, 세션 철회, 비밀번호와 MFA 정책을 구현한다.

## 소유 모듈

- `iam`

## 산출물

- auth APIs
- session store
- security events

## 수용 기준

- 로그인/로그아웃/세션 철회가 동작한다
- 잠금·속도 제한이 적용된다
- 비활성 사용자 세션이 즉시 철회된다

## 필수 리뷰

- `architecture`
- `qa_security`

## 시작 계약

```text
Work Package: WP-PLT-002
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


Phase 0 상세 절차는 `15_PHASE_0_FOUNDATION_IMPLEMENTATION_PLAN.md`의 `WP-PLT-002` 절을 따른다.
