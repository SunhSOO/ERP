# WP-SAL-002 — 품목 카탈로그·견적 버전

- Phase: 2 (CRM·영업·견적·계약)
- 실행 파동: 2.3
- Stream: `commercial`
- 주 담당 역할: Commercial Domain Agent
- 위험도: `critical`
- 상태: `proposed`
- 선행 작업: `WP-SAL-001`, `WP-APR-001`, `WP-DMS-001`

## 목표

견적 계산, 버전, 결재, PDF 계약을 구현한다.

## 소유 모듈

- `sales`

## 산출물

- catalog
- quote APIs
- PDF template

## 수용 기준

- 공급가/세액/합계 계산이 정확하다
- 발송 견적은 새 버전으로만 수정한다
- 원가/마진 권한이 분리된다

## 필수 리뷰

- `architecture`
- `qa_security`

## 시작 계약

```text
Work Package: WP-SAL-002
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

