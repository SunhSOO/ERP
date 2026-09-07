# WP-CRM-002 — 리드·영업활동

- Phase: 2 (CRM·영업·견적·계약)
- 실행 파동: 2.2
- Stream: `commercial`
- 주 담당 역할: Commercial Domain Agent
- 위험도: `medium`
- 상태: `proposed`
- 선행 작업: `WP-CRM-001`, `WP-CAL-001`

## 목표

리드 전환과 전화/메일/미팅/후속 활동을 관리한다.

## 소유 모듈

- `crm`

## 산출물

- lead conversion
- activity timeline
- follow-up alerts

## 수용 기준

- 전환 결과가 고객/담당자/기회와 연결된다
- 중복 전환을 방지한다
- 후속 활동이 일정/알림과 연결된다

## 필수 리뷰

- `domain_owner`
- `qa`

## 시작 계약

```text
Work Package: WP-CRM-002
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

