# WP-ANL-002 — 정기 보고서 생성·배포

- Phase: 7 (외부 연동·분석·인프라 고도화)
- 실행 파동: 7.2
- Stream: `analytics`
- 주 담당 역할: Analytics Agent
- 위험도: `high`
- 상태: `proposed`
- 선행 작업: `WP-ANL-001`, `WP-INT-MAIL-001`, `WP-AI-002`

## 목표

저장된 보고서를 예약 생성하고 승인된 수신자에게 전달한다.

## 소유 모듈

- `analytics`

## 산출물

- report scheduler
- PDF/export
- delivery audit

## 수용 기준

- 실패한 생성/발송을 재시도한다
- AI 서술과 공식 수치를 구분한다
- 발송 이력과 결과 파일을 보존한다

## 필수 리뷰

- `architecture`
- `qa_security`

## 시작 계약

```text
Work Package: WP-ANL-002
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

