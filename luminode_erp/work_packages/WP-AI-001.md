# WP-AI-001 — AI Gateway·대화·모델 정책

- Phase: 5 (검색·지식·AI 읽기 기능)
- 실행 파동: 5.5
- Stream: `ai_search`
- 주 담당 역할: AI·Search Agent
- 위험도: `critical`
- 상태: `proposed`
- 선행 작업: `WP-RAG-002`, `WP-OPS-002`

## 목표

대화, 스트리밍, 모델 라우팅, 실행 trace 기반을 만든다.

## 소유 모듈

- `ai`

## 산출물

- AI gateway
- conversation storage
- model policy

## 수용 기준

- 민감도에 따른 모델 정책이 적용된다
- 대화 보존/삭제 정책이 동작한다
- AI 장애가 ERP CRUD를 막지 않는다

## 필수 리뷰

- `architecture`
- `qa_security`

## 시작 계약

```text
Work Package: WP-AI-001
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

