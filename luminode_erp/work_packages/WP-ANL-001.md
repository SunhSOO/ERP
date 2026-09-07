# WP-ANL-001 — 표준 KPI·리포트

- Phase: 7 (외부 연동·분석·인프라 고도화)
- 실행 파동: 7.1
- Stream: `analytics`
- 주 담당 역할: Analytics Agent
- 위험도: `high`
- 상태: `proposed`
- 선행 작업: `WP-FIN-003`, `WP-SAL-001`, `WP-PRJ-003`

## 목표

역할별 공식 KPI와 프로젝트/영업/재무 보고서를 구현한다.

## 소유 모듈

- `analytics`

## 산출물

- metric definitions
- report APIs
- drill-down UI

## 수용 기준

- 모든 KPI 정의가 문서화된다
- 집계 수치가 원본과 일치한다
- 기준일/필터가 표시된다

## 필수 리뷰

- `architecture`
- `qa_security`

## 시작 계약

```text
Work Package: WP-ANL-001
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

