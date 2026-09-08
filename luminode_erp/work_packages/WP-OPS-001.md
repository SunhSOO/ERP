# WP-OPS-001 — Docker Compose 개발·스테이징 기반

- Phase: 0 (기반 플랫폼)
- 실행 파동: 0.2
- Stream: `infra`
- 주 담당 역할: DevOps Agent
- 위험도: `high`
- 상태: `proposed`
- 선행 작업: `WP-PLT-001`

## 목표

ERP 핵심 서비스의 재현 가능한 컨테이너 환경을 만든다.

## 소유 모듈

- `operations`

## 산출물

- compose manifests
- health checks
- environment templates

## 수용 기준

- PostgreSQL/Redis/MinIO와 앱이 health 상태로 기동한다
- 데이터 서비스 포트가 불필요하게 외부 노출되지 않는다
- 이미지 버전이 고정된다

## 필수 리뷰

- `architecture`
- `qa_security`

## 시작 계약

```text
Work Package: WP-OPS-001
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


Phase 0 상세 절차는 `15_PHASE_0_FOUNDATION_IMPLEMENTATION_PLAN.md`의 `WP-OPS-001` 절을 따른다.
