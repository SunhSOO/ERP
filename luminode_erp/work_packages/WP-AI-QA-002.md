# WP-AI-QA-002 — AI 도구 안전 게이트

- Phase: 6 (승인형 AI 업무 실행)
- 실행 파동: 6.5
- Stream: `qa`
- 주 담당 역할: QA·Security Agent
- 위험도: `critical`
- 상태: `proposed`
- 선행 작업: `WP-AIT-002`, `WP-AIA-002`, `WP-AIO-001`

## 목표

승인 우회, 중복 실행, payload 변조, 인젝션을 검증한다.

## 소유 모듈

- `qa`
- `ai`

## 산출물

- tool safety suite
- approval bypass tests
- chaos/failure tests

## 수용 기준

- R4 실행 승인 우회 0건
- idempotency 회귀 통과
- 도구 장애 시 부분 결과가 명확하다

## 필수 리뷰

- `architecture`
- `qa_security`

## 시작 계약

```text
Work Package: WP-AI-QA-002
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

