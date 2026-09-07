# WP-HR-001 — 인사 프로필·기술·자격

- Phase: 4 (인사·근태·휴가)
- 실행 파동: 4.1
- Stream: `people`
- 주 담당 역할: People/HR Domain Agent
- 위험도: `critical`
- 상태: `proposed`
- 선행 작업: `WP-PLT-003`, `WP-QA-P3`

## 목표

직원 이력과 제한된 민감정보, 기술·자격을 관리한다.

## 소유 모듈

- `hr`

## 산출물

- employee profile extension
- skills/certifications
- privacy controls

## 수용 기준

- 민감 필드가 분리/마스킹된다
- 자격 만료 알림이 가능하다
- 프로젝트 이력과 연결된다

## 필수 리뷰

- `architecture`
- `qa_security`

## 시작 계약

```text
Work Package: WP-HR-001
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

