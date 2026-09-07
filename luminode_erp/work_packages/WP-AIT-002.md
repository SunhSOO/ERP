# WP-AIT-002 — AI 승인 요청·고정 payload·재개

- Phase: 6 (승인형 AI 업무 실행)
- 실행 파동: 6.2
- Stream: `ai_tools`
- 주 담당 역할: AI Tooling Agent
- 위험도: `critical`
- 상태: `proposed`
- 선행 작업: `WP-AIT-001`, `WP-APR-002`

## 목표

고위험 실행을 사람 승인 후 재개하는 런타임을 구현한다.

## 소유 모듈

- `ai-tools`
- `workflow`

## 산출물

- AI approval queue
- payload sealing
- resume/cancel

## 수용 기준

- 승인 전 실행이 불가하다
- 승인 후 payload 변조가 차단된다
- 만료/거절/취소가 추적된다

## 필수 리뷰

- `architecture`
- `qa_security`

## 시작 계약

```text
Work Package: WP-AIT-002
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

