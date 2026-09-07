# WP-SRCH-001 — 통합 키워드 검색·색인

- Phase: 5 (검색·지식·AI 읽기 기능)
- 실행 파동: 5.1
- Stream: `ai_search`
- 주 담당 역할: AI·Search Agent
- 위험도: `critical`
- 상태: `proposed`
- 선행 작업: `WP-QA-P1`, `WP-DMS-001`, `WP-PLT-005`

## 목표

권한 메타데이터를 가진 업무/문서 검색을 구현한다.

## 소유 모듈

- `search`

## 산출물

- indexing pipeline
- search API
- reindex tools

## 수용 기준

- DB 변경이 증분 색인된다
- 검색 결과를 원본 권한으로 재검증한다
- 색인 실패를 재처리한다

## 필수 리뷰

- `architecture`
- `qa_security`

## 시작 계약

```text
Work Package: WP-SRCH-001
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

