# WP-CRM-001 — 고객사·담당자

- Phase: 2 (CRM·영업·견적·계약)
- 실행 파동: 2.1
- Stream: `commercial`
- 주 담당 역할: Commercial Domain Agent
- 위험도: `high`
- 상태: `proposed`
- 선행 작업: `WP-QA-000`

## 목표

고객 조직과 담당자, 중복 후보를 관리한다.

## 소유 모듈

- `crm`

## 산출물

- account/contact APIs
- duplicate detection
- CRM screens

## 수용 기준

- 사업자번호/도메인 중복 경고가 동작한다
- 고객 접근 권한과 민감 메모가 분리된다
- 프로젝트/계약 링크가 제공된다

## 필수 리뷰

- `architecture`
- `qa_security`

## 시작 계약

```text
Work Package: WP-CRM-001
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

