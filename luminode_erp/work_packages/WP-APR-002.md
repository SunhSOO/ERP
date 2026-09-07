# WP-APR-002 — 조건부 결재·대결·SLA

- Phase: 3 (결재·구매·재무·자산)
- 실행 파동: 3.1
- Stream: `operations`
- 주 담당 역할: Operations Domain Agent
- 위험도: `critical`
- 상태: `proposed`
- 선행 작업: `WP-APR-001`, `WP-QA-P2`

## 목표

금액/조직 조건 결재선과 지연·대결 정책을 고도화한다.

## 소유 모듈

- `workflow`

## 산출물

- routing rules
- delegation
- SLA alerts

## 수용 기준

- 금액 한도별 결재선이 정확하다
- 승인 payload가 변경되지 않는다
- 기한 경과와 대결 이력이 남는다

## 필수 리뷰

- `architecture`
- `qa_security`

## 시작 계약

```text
Work Package: WP-APR-002
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

