# WP-INT-MAIL-001 — 이메일 발송·활동 연결

- Phase: 7 (외부 연동·분석·인프라 고도화)
- 실행 파동: 7.1
- Stream: `integration`
- 주 담당 역할: Integration Agent
- 위험도: `critical`
- 상태: `proposed`
- 선행 작업: `WP-CRM-002`, `WP-SAL-002`, `WP-PLT-007`

## 목표

견적/계약/알림 발송과 수신 활동 연결을 구현한다.

## 소유 모듈

- `email-integration`

## 산출물

- email adapter
- safe recipient preview
- thread mapping

## 수용 기준

- 외부 발송에 승인/미리보기가 적용된다
- 스테이징 발송이 안전 처리된다
- 중복 메시지가 방지된다

## 필수 리뷰

- `architecture`
- `qa_security`

## 시작 계약

```text
Work Package: WP-INT-MAIL-001
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

