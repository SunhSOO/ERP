# WP-AIA-002 — 교차 모듈 승인형 자동화

- Phase: 6 (승인형 AI 업무 실행)
- 실행 파동: 6.4
- Stream: `ai_tools`
- 주 담당 역할: AI Tooling Agent
- 위험도: `critical`
- 상태: `proposed`
- 선행 작업: `WP-AIA-001`, `WP-AUT-001`, `WP-AUT-002`

## 목표

계약→프로젝트, 회의→업무, 입고→자산 워크플로우를 AI에서 실행한다.

## 소유 모듈

- `ai-tools`
- `automation`

## 산출물

- cross-domain plans
- approval previews
- compensation/retry

## 수용 기준

- 부분 실패를 숨기지 않는다
- 각 단계의 권한과 감사가 적용된다
- 동일 원본 재실행 중복이 없다

## 필수 리뷰

- `architecture`
- `qa_security`

## 시작 계약

```text
Work Package: WP-AIA-002
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

