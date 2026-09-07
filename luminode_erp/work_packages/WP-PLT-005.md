# WP-PLT-005 — 감사 로그·활동 로그·Outbox

- Phase: 0 (기반 플랫폼)
- 실행 파동: 0.6
- Stream: `platform`
- 주 담당 역할: Platform Backend Agent
- 위험도: `critical`
- 상태: `proposed`
- 선행 작업: `WP-PLT-004`

## 목표

중요 변경 추적과 신뢰성 있는 이벤트 발행 기반을 만든다.

## 소유 모듈

- `core`
- `collab`

## 산출물

- audit log
- activity timeline
- outbox publisher

## 수용 기준

- 중요 command가 actor/before/after/trace를 남긴다
- outbox 중복 소비가 방지된다
- 일반 앱 권한으로 감사 로그를 수정하지 못한다

## 필수 리뷰

- `architecture`
- `qa_security`

## 시작 계약

```text
Work Package: WP-PLT-005
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


Phase 0 상세 절차는 `15_PHASE_0_FOUNDATION_IMPLEMENTATION_PLAN.md`의 `WP-PLT-005` 절을 따른다.
