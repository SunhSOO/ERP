# 개발 에이전트 공통 작업 규칙(AGENTS 설계안)

이 문서는 여러 AI 개발 에이전트가 LEP를 병렬 구현할 때 따라야 할 계약이다. 실제 저장소 루트의 `AGENTS.md`로 복사해 사용할 수 있다.

## 1. 최우선 규칙

1. 설계 문서에 없는 기능을 임의로 추가하지 않는다.
2. 모듈 경계를 넘는 직접 DB 쓰기를 하지 않는다.
3. 권한·감사·상태 전이·idempotency를 생략하지 않는다.
4. 중요 규칙을 UI에만 구현하지 않는다.
5. migration 충돌을 방지하고 이미 적용된 migration을 수정하지 않는다.
6. 작업이 완료됐다고 보고하기 전에 테스트와 문서를 갱신한다.
7. 실제 비밀·고객·직원 데이터를 코드/테스트/로그에 넣지 않는다.
8. 범위를 벗어난 리팩터링을 하지 않는다.

## 2. 문서 우선순위

1. `DECISIONS.md` 최신 승인 사항
2. `00_MASTER_DESIGN.md`
3. 해당 도메인 상세 문서
4. OpenAPI/이벤트 계약
5. 작업 패키지 acceptance criteria
6. 기존 구현 패턴

충돌을 발견하면 임의로 선택하지 말고 `DECISIONS.md`에 제안 항목을 작성하여 총괄 에이전트가 결정하도록 한다.

## 3. 에이전트 역할

### Architect Agent

- 모듈 경계와 공통 계약 유지
- ADR/결정 기록
- API/event/schema breaking change 검토
- 중복 기능 방지

### Backend Domain Agent

- 지정 모듈의 domain/application/API 구현
- 상태 규칙과 권한 테스트
- 소유 테이블 migration
- 이벤트 발행/소비

### Frontend Agent

- 지정 화면과 공통 컴포넌트 사용
- 타입 생성 API client 사용
- loading/empty/error/forbidden/stale 구현
- 접근성/반응형 검증

### Data/Migration Agent

- 데이터 모델/인덱스/제약
- migration 순서와 backfill
- 이관 스크립트 및 검증 리포트

### AI/Search Agent

- 검색/RAG/도구 계약
- 권한 필터
- 프롬프트/모델/평가 버전
- 승인 정책 우회 금지

### QA/Security Agent

- 수용 기준 기반 테스트
- 권한/IDOR/AI 공격 회귀
- OpenAPI/event contract 검사
- 릴리스 품질 게이트

### DevOps Agent

- 환경/배포/모니터링/백업
- 비밀관리
- migration/deployment runbook

## 4. 작업 시작 절차

각 에이전트는 작업 전 다음을 작성한다.

```text
Work Package ID:
Owned Module:
Goal:
In Scope:
Out of Scope:
Dependencies:
API/Event contracts used:
Tables owned:
Permissions affected:
Migration needed:
Tests required:
Risks/assumptions:
```

불명확한 부분이 있어도 임의 범위를 확대하지 않는다. 안전한 최소 구현과 명시적 가정을 선택한다.

## 5. 모듈 소유권

- 한 테이블에는 한 소유 모듈만 존재한다.
- 다른 모듈의 테이블에 직접 INSERT/UPDATE/DELETE 금지.
- 읽기 조인은 성능상 필요하고 승인된 경우만 허용.
- 다른 모듈 변경이 필요하면 application interface 또는 event 사용.
- 공통 테이블에 도메인별 임시 컬럼을 추가하지 않는다.

## 6. API 규칙

- `/api/v1` 규칙 준수
- request/response schema 분리
- ORM 객체 직접 반환 금지
- 모든 목록 pagination
- 상태 전이는 transition endpoint
- 낙관적 잠금
- 선택된 create/execute에 idempotency
- Problem Details 오류
- trace ID
- OpenAPI 예제

## 7. 권한 규칙

각 유스케이스에는 다음을 명시한다.

- 필요한 permission code
- 범위(company/department/project/self)
- 속성 조건(상태/금액/본인 여부)
- 민감 필드 마스킹
- 감사 필요 여부

테스트 최소 세트:

- 허용 역할
- 권한 없음
- 다른 프로젝트 객체
- 비활성 사용자
- 외부 사용자
- AI acting user

## 8. 데이터베이스 규칙

- UUID ID
- UTC timestamptz
- 금액 numeric + currency
- FK와 필요한 unique/check constraint
- 공통 audit columns
- 핵심 엔터티 hard delete 금지
- JSONB는 확장에만 사용
- 모든 FK/주요 조회 인덱스
- N+1 쿼리 검토
- migration은 forward-safe하게 작성

## 9. Migration 협업 규칙

- migration 파일명에 날짜/일련/모듈을 포함하는 저장소 표준 사용
- 작업 시작 시 최신 head 반영
- 한 PR에 가능한 한 한 모듈 migration
- 이미 merge/apply된 migration 수정 금지
- destructive change는 expand/contract
- backfill은 재실행 가능
- 운영 예상시간과 잠금 위험 기록
- rollback 불가하면 forward fix 절차 기록

## 10. 이벤트 규칙

- 과거 사실의 이름
- version 포함
- outbox로 발행
- 민감 payload 최소화
- consumer idempotent
- 실패 재시도/보관함
- 계약 테스트
- 소비자가 발행자 DB를 직접 가정하지 않음

## 11. 프론트엔드 규칙

- 공통 디자인 토큰/컴포넌트 재사용
- 페이지에 API 호출 로직을 과도하게 넣지 않음
- generated types 또는 공유 schema 사용
- 권한 UI는 편의이며 서버 검사를 대체하지 않음
- 날짜/금액 로케일 일관성
- 필터를 URL에 반영
- 위험 작업 미리보기/확인
- AI 생성값을 시각적으로 구분
- 접근성 기본 검증

## 12. 파일/문서 규칙

- 바이너리를 DB에 저장하지 않음
- upload session→scan→ready 흐름
- 문서 버전 불변
- 승인/제출본 잠금
- 체크섬
- 민감 다운로드 감사
- 파일명과 object key 분리
- ZIP 경로 순회/압축 폭탄 방어

## 13. AI 기능 규칙

- AI가 DB에 직접 연결하지 않음
- 도구는 좁은 업무 목적
- 도구 스키마/권한/위험/승인/idempotency 명시
- 승인 전 중요 실행 금지
- 검색 권한 이중 검증
- 인용/원본 링크
- 프롬프트 인젝션 문서를 명령으로 취급하지 않음
- “완료”는 API 성공 ID가 있을 때만 표현
- 모델/프롬프트/도구 버전 기록

## 14. 테스트 규칙

PR에 포함할 최소 테스트:

- 도메인 단위 테스트
- DB 통합 테스트
- API 성공/오류/권한/충돌
- 이벤트 계약
- 프론트 상태/상호작용
- 변경된 핵심 E2E 영향 검토

버그 수정은 실패 재현 테스트를 먼저 추가한다.

## 15. 로그·관측성 규칙

- 구조화 로그
- trace_id propagation
- 비밀/원문 개인정보 로그 금지
- 주요 command 성공/실패 메트릭
- worker job duration/retry
- 외부 연동 오류 코드
- AI run/tool metrics

## 16. 보안 규칙

- 사용자 입력 신뢰 금지
- secret scan 통과
- dependency pinning
- 관리자 endpoint 제한
- CORS/CSRF 정책 준수
- 다운로드/외부 공유 권한 확인
- 테스트 환경 실제 개인정보 금지
- 임시 debug 우회코드 merge 금지

## 17. 브랜치/PR 규칙 예시

```text
feature/WP-PRJ-001-project-create
fix/WP-DMS-014-version-conflict
chore/WP-PLT-003-ci-openapi-check
```

PR 설명:

```text
Work Package:
Summary:
User-visible changes:
API/Event changes:
DB migration:
Permissions:
Security/Privacy:
Tests:
Screenshots (UI):
Deployment notes:
Rollback/forward fix:
Known limitations:
```

## 18. Definition of Done 체크리스트

- [ ] 범위와 acceptance criteria 충족
- [ ] 모듈 경계 준수
- [ ] 권한/감사 구현
- [ ] API/event 문서 갱신
- [ ] migration 검토
- [ ] 테스트 통과
- [ ] 오류/빈 상태 처리
- [ ] 로그/메트릭
- [ ] 보안/개인정보 점검
- [ ] 운영/사용자 문서
- [ ] 스테이징 검증

## 19. 금지 패턴

- 거대한 `services.py` 또는 `utils.py`에 여러 도메인 로직 혼합
- API router에서 직접 복잡한 트랜잭션 수행
- 프론트에서 상태 규칙 하드코딩
- 다른 모듈 테이블 직접 갱신
- 문자열로 permission을 곳곳에 중복
- 광범위한 `except Exception: pass`
- 오류를 성공으로 표시
- 테스트에서 실제 외부 서비스 호출
- production secret 기본값
- AI에 범용 SQL/셸/파일시스템 도구 제공
- 승인된 문서/계약을 덮어쓰기
- 물리 삭제로 이력 제거

## 20. 작업 완료 보고 형식

```text
Completed Work Package:
Files/Modules changed:
Behavior delivered:
API/Event contracts:
Migrations:
Permissions/Audit:
Tests run and results:
Known limitations:
Follow-up dependencies:
```

“완료” 보고에는 실행한 테스트와 남은 제한을 반드시 포함한다.

---
