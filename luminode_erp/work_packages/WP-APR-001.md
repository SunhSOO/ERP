# WP-APR-001 — 일반 전자결재

- Phase: 1 (프로젝트 운영 코어)
- 실행 파동: 1.1
- Stream: `operations`
- 주 담당 역할: Operations Domain Agent
- 위험도: `critical`
- 상태: `proposed`
- 선행 작업: `WP-PLT-003`, `WP-PLT-004`, `WP-PLT-005`, `WP-PLT-007`

## 목표

순차/병렬 결재, 반려, 회수, 재상신의 공통 엔진을 구현한다.

## 소유 모듈

- `workflow`

## 산출물

- approval engine
- approval inbox
- template baseline

## 수용 기준

- 승인 단계와 대결을 추적한다
- 자기승인 제한이 가능하다
- 완료 스냅샷과 감사가 남는다

## 필수 리뷰

- `architecture`
- `qa_security`

## 시작 계약

```text
Work Package: WP-APR-001
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

