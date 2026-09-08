# WP-RAG-001 — 문서 추출·청크·임베딩 파이프라인

- Phase: 5 (검색·지식·AI 읽기 기능)
- 실행 파동: 5.3
- Stream: `ai_search`
- 주 담당 역할: AI·Search Agent
- 위험도: `critical`
- 상태: `proposed`
- 선행 작업: `WP-SRCH-001`, `WP-KMS-001`

## 목표

지원 문서를 안전하게 텍스트/청크/벡터로 색인한다.

## 소유 모듈

- `rag`

## 산출물

- extractors
- chunk metadata
- embedding jobs

## 수용 기준

- 원문 위치와 버전이 보존된다
- 구버전 벡터가 비활성화된다
- 악성/실행 파일이 인덱싱되지 않는다

## 필수 리뷰

- `architecture`
- `qa_security`

## 시작 계약

```text
Work Package: WP-RAG-001
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

