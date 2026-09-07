# WP-INF-002 — 장애·포스트모템

- Phase: 7 (외부 연동·분석·인프라 고도화)
- 실행 파동: 7.2
- Stream: `infra_integration`
- 주 담당 역할: Infrastructure Integration Agent
- 위험도: `high`
- 상태: `proposed`
- 선행 작업: `WP-INF-001`, `WP-PRJ-004`

## 목표

서비스 장애의 상태, 조치, 원인, 회고를 관리한다.

## 소유 모듈

- `infra`

## 산출물

- incident workflow
- postmortem template
- notifications

## 수용 기준

- SEV 상태와 타임라인이 보존된다
- 장애와 프로젝트/자산/배포가 연결된다
- 재발 방지 업무를 생성한다

## 필수 리뷰

- `architecture`
- `qa_security`

## 시작 계약

```text
Work Package: WP-INF-002
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

