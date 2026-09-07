# WP-AI-QA-001 — RAG·AI 읽기 보안 게이트

- Phase: 5 (검색·지식·AI 읽기 기능)
- 실행 파동: 5.7
- Stream: `qa`
- 주 담당 역할: QA·Security Agent
- 위험도: `critical`
- 상태: `proposed`
- 선행 작업: `WP-AI-002`, `WP-AI-003`, `WP-AI-004`

## 목표

권한 누출, 인용, 최신성, 인젝션을 평가한다.

## 소유 모듈

- `qa`
- `ai`

## 산출물

- AI evaluation set
- prompt injection suite
- quality dashboard

## 수용 기준

- 권한 누출 0건
- 최신 버전/인용 회귀를 통과한다
- 모델/프롬프트 버전별 결과가 추적된다

## 필수 리뷰

- `architecture`
- `qa_security`

## 시작 계약

```text
Work Package: WP-AI-QA-001
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

