# WP-KMS-001 — 위키·지식 수명주기

- Phase: 5 (검색·지식·AI 읽기 기능)
- 실행 파동: 5.2
- Stream: `ai_search`
- 주 담당 역할: AI·Search Agent
- 위험도: `high`
- 상태: `proposed`
- 선행 작업: `WP-DMS-001`, `WP-SRCH-001`

## 목표

정책/가이드/FAQ의 버전, 검토일, 대체 관계를 구현한다.

## 소유 모듈

- `knowledge`

## 산출물

- article APIs
- review workflow
- knowledge UI

## 수용 기준

- 게시/폐기/대체 상태가 추적된다
- 오래된 지식이 표시된다
- RAG 포함 여부를 통제한다

## 필수 리뷰

- `architecture`
- `qa_security`

## 시작 계약

```text
Work Package: WP-KMS-001
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

