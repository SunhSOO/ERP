# WP-INT-CAL-001 — 외부 캘린더 동기화

- Phase: 7 (외부 연동·분석·인프라 고도화)
- 실행 파동: 7.1
- Stream: `integration`
- 주 담당 역할: Integration Agent
- 위험도: `high`
- 상태: `proposed`
- 선행 작업: `WP-CAL-001`

## 목표

ERP 일정과 승인된 외부 캘린더를 충돌 없이 동기화한다.

## 소유 모듈

- `calendar-integration`

## 산출물

- calendar adapter
- mapping/conflict UI
- sync jobs

## 수용 기준

- external ID/version을 추적한다
- 충돌을 자동 덮어쓰지 않는다
- 외부 장애가 ERP 일정을 막지 않는다

## 필수 리뷰

- `architecture`
- `qa_security`

## 시작 계약

```text
Work Package: WP-INT-CAL-001
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

