# WP-AIO-001 — AI 관측성·비용·킬스위치

- Phase: 6 (승인형 AI 업무 실행)
- 실행 파동: 6.2
- Stream: `ai_tools`
- 주 담당 역할: AI Tooling Agent
- 위험도: `high`
- 상태: `proposed`
- 선행 작업: `WP-AIT-001`, `WP-AI-001`

## 목표

실행 단계, 오류, 비용, 모델/도구 버전과 긴급 중지를 관리한다.

## 소유 모듈

- `ai-ops`

## 산출물

- run dashboards
- cost metrics
- kill switches

## 수용 기준

- 실행별 trace를 재구성할 수 있다
- 모델/도구를 즉시 중지한다
- 민감 원문이 운영 로그에 과다 노출되지 않는다

## 필수 리뷰

- `architecture`
- `qa_security`

## 시작 계약

```text
Work Package: WP-AIO-001
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

