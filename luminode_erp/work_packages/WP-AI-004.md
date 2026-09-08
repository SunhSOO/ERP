# WP-AI-004 — 산출물 누락·버전 점검

- Phase: 5 (검색·지식·AI 읽기 기능)
- 실행 파동: 5.6
- Stream: `ai_search`
- 주 담당 역할: AI·Search Agent
- 위험도: `high`
- 상태: `proposed`
- 선행 작업: `WP-AI-001`, `WP-DMS-002`, `WP-CON-002`

## 목표

템플릿/계약/산출물 상태를 비교해 조치 후보를 만든다.

## 소유 모듈

- `ai`
- `dms`

## 산출물

- deliverable audit
- version mismatch checks
- action suggestions

## 수용 기준

- 누락/미승인/제출 불일치를 분류한다
- 예외 승인 산출물을 오탐하지 않는다
- 결과가 원본 링크를 포함한다

## 필수 리뷰

- `architecture`
- `qa_security`

## 시작 계약

```text
Work Package: WP-AI-004
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

