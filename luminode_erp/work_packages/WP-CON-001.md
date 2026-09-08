# WP-CON-001 — 계약·버전·보안등급

- Phase: 2 (CRM·영업·견적·계약)
- 실행 파동: 2.4
- Stream: `commercial`
- 주 담당 역할: Commercial Domain Agent
- 위험도: `critical`
- 상태: `proposed`
- 선행 작업: `WP-CRM-001`, `WP-SAL-002`, `WP-APR-001`, `WP-DMS-001`

## 목표

계약 상태, 서명본, 변경계약, 접근 통제를 구현한다.

## 소유 모듈

- `contract`

## 산출물

- contract APIs
- version compare
- contract permissions

## 수용 기준

- ACTIVE 조건이 검증된다
- 계약 변경 이력이 보존된다
- 민감 문서 접근과 다운로드가 감사된다

## 필수 리뷰

- `architecture`
- `qa_security`

## 시작 계약

```text
Work Package: WP-CON-001
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

