# WP-PLT-001 — 저장소·모듈 경계 부트스트랩

- Phase: 0 (기반 플랫폼)
- 실행 파동: 0.1
- Stream: `platform`
- 주 담당 역할: Platform Backend Agent
- 위험도: `high`
- 상태: `proposed`
- 선행 작업: 없음

## 목표

백엔드/프론트/인프라의 공통 구조와 모듈 경계 검사 기반을 만든다.

## 소유 모듈

- `core`

## 산출물

- repository structure
- module boundary rules
- developer commands

## 수용 기준

- 모든 모듈이 표준 구조를 사용한다
- CI에서 금지된 cross-module import를 탐지한다
- 개발 환경이 문서대로 재현된다

## 필수 리뷰

- `architecture`
- `qa_security`

## 시작 계약

```text
Work Package: WP-PLT-001
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


Phase 0 상세 절차는 `15_PHASE_0_FOUNDATION_IMPLEMENTATION_PLAN.md`의 `WP-PLT-001` 절을 따른다.
