# WP-QA-000 — Phase 0 보안·복구 게이트

- Phase: 0 (기반 플랫폼)
- 실행 파동: 0.9
- Stream: `qa`
- 주 담당 역할: QA·Security Agent
- 위험도: `critical`
- 상태: `proposed`
- 선행 작업: `WP-PLT-002`, `WP-PLT-003`, `WP-PLT-004`, `WP-PLT-005`, `WP-PLT-006`, `WP-PLT-007`, `WP-UI-001`, `WP-OPS-002`

## 목표

기반 플랫폼의 인증, 권한, 파일, 감사, 복구를 검증한다.

## 소유 모듈

- `qa`

## 산출물

- security regression suite
- foundation E2E
- restore evidence

## 수용 기준

- IDOR/세션/악성 업로드 테스트를 통과한다
- 신규 환경 복원이 가능하다
- Critical/High 결함이 없다

## 필수 리뷰

- `architecture`
- `qa_security`

## 시작 계약

```text
Work Package: WP-QA-000
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


Phase 0 상세 절차는 `15_PHASE_0_FOUNDATION_IMPLEMENTATION_PLAN.md`의 `WP-QA-000` 절을 따른다.
