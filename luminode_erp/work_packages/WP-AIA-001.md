# WP-AIA-001 — 업무·리스크·검토요청 쓰기 도구

- Phase: 6 (승인형 AI 업무 실행)
- 실행 파동: 6.3
- Stream: `ai_tools`
- 주 담당 역할: AI Tooling Agent
- 위험도: `critical`
- 상태: `proposed`
- 선행 작업: `WP-AIT-002`, `WP-PRJ-004`, `WP-DMS-002`

## 목표

낮은/중간 위험의 프로젝트 도구를 dry-run과 함께 제공한다.

## 소유 모듈

- `ai-tools`
- `project`

## 산출물

- task tools
- risk tools
- review request tools

## 수용 기준

- 미리보기와 실제 결과가 일치한다
- 재시도해도 중복이 없다
- 결과 엔터티 링크가 반환된다

## 필수 리뷰

- `architecture`
- `qa_security`

## 시작 계약

```text
Work Package: WP-AIA-001
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

