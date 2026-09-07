# WP-QA-FINAL — 전사 릴리스·재해복구 게이트

- Phase: 7 (외부 연동·분석·인프라 고도화)
- 실행 파동: 7.3
- Stream: `qa`
- 주 담당 역할: QA·Security Agent
- 위험도: `critical`
- 상태: `proposed`
- 선행 작업: `WP-AI-QA-002`, `WP-INT-GIT-001`, `WP-INT-CAL-001`, `WP-INT-MAIL-001`, `WP-INF-002`, `WP-ANL-002`, `WP-OPS-HA-001`

## 목표

전체 핵심 여정, 보안, 데이터, 백업/복구를 최종 검증한다.

## 소유 모듈

- `qa`
- `operations`

## 산출물

- full regression
- DR exercise
- release readiness report

## 수용 기준

- Critical/High 결함이 없다
- 복구 목표를 충족하거나 차이를 승인했다
- 운영자/사용자 문서와 책임자가 확정된다

## 필수 리뷰

- `architecture`
- `qa_security`

## 시작 계약

```text
Work Package: WP-QA-FINAL
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

