# WP-AI-003 — 회의 액션아이템 제안

- Phase: 5 (검색·지식·AI 읽기 기능)
- 실행 파동: 5.6
- Stream: `ai_search`
- 주 담당 역할: AI·Search Agent
- 위험도: `high`
- 상태: `proposed`
- 선행 작업: `WP-AI-001`, `WP-CAL-001`, `WP-PRJ-003`

## 목표

회의 전사에서 결정과 액션을 근거와 함께 제안한다.

## 소유 모듈

- `ai`
- `meeting`

## 산출물

- meeting extraction
- assignee/due suggestions
- duplicate check

## 수용 기준

- 근거 위치가 표시된다
- 명시되지 않은 담당/기한은 추천으로 구분된다
- 검토 전 업무가 생성되지 않는다

## 필수 리뷰

- `architecture`
- `qa_security`

## 시작 계약

```text
Work Package: WP-AI-003
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

