# WP-CON-002 — 계약 의무·지급 일정·갱신

- Phase: 2 (CRM·영업·견적·계약)
- 실행 파동: 2.5
- Stream: `commercial`
- 주 담당 역할: Commercial Domain Agent
- 위험도: `high`
- 상태: `proposed`
- 선행 작업: `WP-CON-001`, `WP-DMS-002`

## 목표

산출물/검수 의무와 지급/갱신 계획을 관리한다.

## 소유 모듈

- `contract`

## 산출물

- obligation APIs
- payment schedules
- renewal alerts

## 수용 기준

- 의무와 프로젝트 산출물을 연결한다
- 갱신 90/60/30/7일 알림이 중복 없이 생성된다
- 지급계획과 실제 매출을 구분한다

## 필수 리뷰

- `architecture`
- `qa_security`

## 시작 계약

```text
Work Package: WP-CON-002
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

