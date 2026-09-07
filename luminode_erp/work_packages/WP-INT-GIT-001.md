# WP-INT-GIT-001 — GitHub/GitLab 메타데이터 연동

- Phase: 7 (외부 연동·분석·인프라 고도화)
- 실행 파동: 7.1
- Stream: `integration`
- 주 담당 역할: Integration Agent
- 위험도: `high`
- 상태: `proposed`
- 선행 작업: `WP-QA-P1`, `WP-PLT-005`

## 목표

저장소·이슈·PR·릴리스·CI 상태를 프로젝트와 연결한다.

## 소유 모듈

- `devops-integration`

## 산출물

- webhook adapter
- repository mapping
- task links

## 수용 기준

- 웹훅 중복이 처리되지 않는다
- 소스코드 원문을 불필요하게 복제하지 않는다
- 연동 실패를 재처리한다

## 필수 리뷰

- `architecture`
- `qa_security`

## 시작 계약

```text
Work Package: WP-INT-GIT-001
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

