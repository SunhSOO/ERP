# WP-QA-P2 — Phase 2 수주 여정 게이트

- Phase: 2 (CRM·영업·견적·계약)
- 실행 파동: 2.7
- Stream: `qa`
- 주 담당 역할: QA·Security Agent
- 위험도: `critical`
- 상태: `proposed`
- 선행 작업: `WP-UI-COM-001`

## 목표

고객→영업→견적→계약→프로젝트 E2E를 검증한다.

## 소유 모듈

- `qa`

## 산출물

- commercial E2E
- money calculation tests
- contract permission tests

## 수용 기준

- 견적 버전/계산/결재가 통과한다
- 계약 문서 권한 누출이 없다
- 중복 프로젝트 전환이 없다

## 필수 리뷰

- `architecture`
- `qa_security`

## 시작 계약

```text
Work Package: WP-QA-P2
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

