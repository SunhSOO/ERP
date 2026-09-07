# WP-INF-001 — 서버·서비스·GPU 상태 연동

- Phase: 7 (외부 연동·분석·인프라 고도화)
- 실행 파동: 7.1
- Stream: `infra_integration`
- 주 담당 역할: Infrastructure Integration Agent
- 위험도: `high`
- 상태: `proposed`
- 선행 작업: `WP-OPS-002`, `WP-AST-001`

## 목표

모니터링 경보를 ERP 자산/프로젝트/서비스와 연결한다.

## 소유 모듈

- `infra`

## 산출물

- node/service registry
- alert ingestion
- status dashboard

## 수용 기준

- 원시 시계열은 모니터링 시스템에 남는다
- 중복 경보가 묶인다
- 소유자와 runbook이 표시된다

## 필수 리뷰

- `architecture`
- `qa_security`

## 시작 계약

```text
Work Package: WP-INF-001
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

