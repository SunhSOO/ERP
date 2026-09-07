# WP-HR-002 — 근태·수정 신청

- Phase: 4 (인사·근태·휴가)
- 실행 파동: 4.2
- Stream: `people`
- 주 담당 역할: People/HR Domain Agent
- 위험도: `critical`
- 상태: `proposed`
- 선행 작업: `WP-HR-001`, `WP-APR-002`

## 목표

출퇴근 원장과 누락/수정 결재를 구현한다.

## 소유 모듈

- `hr`

## 산출물

- attendance APIs
- correction approval
- monthly summary

## 수용 기준

- 원 기록과 수정 이력이 남는다
- 권한 없는 타인 근태 조회가 차단된다
- 시간대/공휴일 기준이 일관된다

## 필수 리뷰

- `architecture`
- `qa_security`

## 시작 계약

```text
Work Package: WP-HR-002
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

