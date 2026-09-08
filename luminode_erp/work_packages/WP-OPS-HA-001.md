# WP-OPS-HA-001 — 확장·고가용성 재평가

- Phase: 7 (외부 연동·분석·인프라 고도화)
- 실행 파동: 7.2
- Stream: `infra`
- 주 담당 역할: DevOps Agent
- 위험도: `medium`
- 상태: `proposed`
- 선행 작업: `WP-INF-001`, `WP-ANL-001`

## 목표

실사용 메트릭으로 단일 서버 유지 또는 분리/k3s 전환을 결정한다.

## 소유 모듈

- `operations`

## 산출물

- capacity report
- ADR proposal
- migration option

## 수용 기준

- 실제 부하/장애 데이터를 근거로 한다
- 불필요한 k3s 전환을 하지 않는다
- 비용·운영인력·RTO를 비교한다

## 필수 리뷰

- `domain_owner`
- `qa`

## 시작 계약

```text
Work Package: WP-OPS-HA-001
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

