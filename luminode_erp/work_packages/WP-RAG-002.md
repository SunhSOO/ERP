# WP-RAG-002 — 권한 기반 하이브리드 검색

- Phase: 5 (검색·지식·AI 읽기 기능)
- 실행 파동: 5.4
- Stream: `ai_search`
- 주 담당 역할: AI·Search Agent
- 위험도: `critical`
- 상태: `proposed`
- 선행 작업: `WP-RAG-001`, `WP-PLT-004`

## 목표

키워드+벡터 검색, 재랭킹, 인용을 구현한다.

## 소유 모듈

- `rag`

## 산출물

- hybrid retrieval
- ACL filters
- citation resolver

## 수용 기준

- 다른 프로젝트 자료가 노출되지 않는다
- 최신 승인본이 우선된다
- 인용 링크가 원문 위치로 이동한다

## 필수 리뷰

- `architecture`
- `qa_security`

## 시작 계약

```text
Work Package: WP-RAG-002
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

