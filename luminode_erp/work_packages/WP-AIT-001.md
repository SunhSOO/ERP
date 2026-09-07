# WP-AIT-001 — Tool Registry·스키마·정책 엔진

- Phase: 6 (승인형 AI 업무 실행)
- 실행 파동: 6.1
- Stream: `ai_tools`
- 주 담당 역할: AI Tooling Agent
- 위험도: `critical`
- 상태: `proposed`
- 선행 작업: `WP-AI-QA-001`, `WP-PLT-004`

## 목표

AI 업무 도구를 버전/권한/위험/승인 정책과 함께 등록한다.

## 소유 모듈

- `ai-tools`

## 산출물

- tool registry
- JSON schema validation
- risk policy

## 수용 기준

- 범용 SQL/셸 도구가 없다
- 모든 도구에 permission/risk/idempotency가 있다
- 도구를 즉시 비활성화할 수 있다

## 필수 리뷰

- `architecture`
- `qa_security`

## 시작 계약

```text
Work Package: WP-AIT-001
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

