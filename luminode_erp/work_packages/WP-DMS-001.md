# WP-DMS-001 — 문서·폴더·불변 버전

- Phase: 1 (프로젝트 운영 코어)
- 실행 파동: 1.2
- Stream: `document`
- 주 담당 역할: DMS Agent
- 위험도: `critical`
- 상태: `proposed`
- 선행 작업: `WP-PLT-006`, `WP-PRJ-001`

## 목표

논리 문서, 폴더, 버전, 미리보기 상태를 구현한다.

## 소유 모듈

- `dms`

## 산출물

- document APIs
- version workflow
- document browser

## 수용 기준

- 문서 버전은 수정되지 않는다
- 최신/승인/제출 버전 포인터가 분리된다
- 프로젝트 권한이 폴더/문서에 상속된다

## 필수 리뷰

- `architecture`
- `qa_security`

## 시작 계약

```text
Work Package: WP-DMS-001
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

