# WP-PLT-007 — 댓글·멘션·알림 기반

- Phase: 0 (기반 플랫폼)
- 실행 파동: 0.7
- Stream: `platform`
- 주 담당 역할: Platform Backend Agent
- 위험도: `high`
- 상태: `proposed`
- 선행 작업: `WP-PLT-004`, `WP-PLT-005`

## 목표

모든 엔터티에서 재사용할 협업 및 알림 서비스를 만든다.

## 소유 모듈

- `collab`

## 산출물

- comments APIs
- notification inbox
- delivery worker

## 수용 기준

- 댓글/답글/멘션이 권한 범위를 따른다
- 알림 중복 억제와 읽음 상태가 동작한다
- 이메일 실패가 인앱 알림을 막지 않는다

## 필수 리뷰

- `architecture`
- `qa_security`

## 시작 계약

```text
Work Package: WP-PLT-007
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


Phase 0 상세 절차는 `15_PHASE_0_FOUNDATION_IMPLEMENTATION_PLAN.md`의 `WP-PLT-007` 절을 따른다.
