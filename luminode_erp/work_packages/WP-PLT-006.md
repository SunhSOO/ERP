# WP-PLT-006 — 파일 업로드·검사·MinIO 기반

- Phase: 0 (기반 플랫폼)
- 실행 파동: 0.7
- Stream: `platform`
- 주 담당 역할: Platform Backend Agent
- 위험도: `critical`
- 상태: `proposed`
- 선행 작업: `WP-OPS-001`, `WP-PLT-004`, `WP-PLT-005`

## 목표

안전한 분할 업로드와 file object 메타데이터를 구현한다.

## 소유 모듈

- `dms-core`

## 산출물

- upload session APIs
- malware scan flow
- download authorization

## 수용 기준

- 업로드→검사→READY 상태가 동작한다
- 권한 없는 다운로드가 차단된다
- 체크섬과 파일 크기가 검증된다

## 필수 리뷰

- `architecture`
- `qa_security`

## 시작 계약

```text
Work Package: WP-PLT-006
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


Phase 0 상세 절차는 `15_PHASE_0_FOUNDATION_IMPLEMENTATION_PLAN.md`의 `WP-PLT-006` 절을 따른다.
