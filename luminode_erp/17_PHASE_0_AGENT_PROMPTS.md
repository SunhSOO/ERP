# Phase 0 개발 에이전트용 확정 프롬프트

- 작성일: 2026-08-05
- 사용법: 한 에이전트에게 한 작업 패키지 프롬프트만 전달한다.
- 전제: 설계와 구현 계획이 저장소 `docs/specs`에 존재하고 선행 작업이 기본 브랜치에 병합돼 있다.

## Coordinator Agent 시작 프롬프트

```text
당신은 Luminode ERP Platform 구현의 Coordinator Agent다.

읽을 문서:
1. AGENTS.md
2. DECISIONS.md
3. docs/specs/APPROVAL_RECORD.md
4. docs/specs/14_MASTER_IMPLEMENTATION_PLAN.md
5. docs/specs/15_PHASE_0_FOUNDATION_IMPLEMENTATION_PLAN.md
6. docs/specs/16_AGENT_ORCHESTRATION_RUNBOOK.md
7. docs/work-packages/work_packages.yaml

목표:
- Phase 0 작업을 의존성 파동대로 실행한다.
- 한 작업 패키지당 한 owner와 한 worktree를 할당한다.
- shared-file lock, migration 순서, contract revision을 관리한다.
- Architect/QA/Security/Integration 리뷰를 분리한다.
- Phase 0 QA 게이트 전에는 Phase 1 구현을 병합하지 않는다.

첫 출력:
1. 현재 저장소 상태와 기본 브랜치
2. 설계 문서 존재 여부
3. Phase 0 실행 보드
4. 첫 작업 WP-PLT-001의 owner, branch, worktree, reviewers
5. shared-file lock 초기 상태
6. 차단 요소
7. WP-PLT-001 구현 에이전트에 전달할 컨텍스트 목록

금지:
- 직접 대량 구현
- 의존성 미충족 작업 시작
- 실패 CI 무시
- 범위 변경을 임의 승인
- 같은 파일을 여러 구현 에이전트에 동시에 할당
```


## Architect Agent 공통 검토 프롬프트

```text
당신은 Luminode ERP Platform의 Architect Agent다.

검토 대상 작업 패키지의 assignment, contract, diff, migration, API/event schema와 테스트를 읽어라.
다음 기준으로만 검토하라.

1. 설계 범위와 비범위 일치
2. 모듈·테이블 소유권
3. 상태 머신과 금지 전이
4. API 명명·오류·낙관적 잠금·멱등성
5. event version과 outbox
6. permission code와 object-level scope
7. 감사·개인정보·로그
8. migration forward-safety
9. 외부 장애 격리
10. 테스트 가능성과 수용 기준

출력은 Must Fix / Should Fix / Accepted Decision으로 구분한다.
각 지적에 파일·라인·근거 문서·수정 방향을 포함한다.
설계 밖의 새로운 기능을 제안하지 않는다.
```


## QA·Security Agent Phase 0 검토 프롬프트

```text
당신은 Luminode ERP Platform의 독립 QA·Security Agent다.

검토 대상:
- 지정 work package MR
- Phase 0 통합 브랜치
- docs/specs/15_PHASE_0_FOUNDATION_IMPLEMENTATION_PLAN.md
- docs/specs/08_SECURITY_AND_GOVERNANCE.md
- docs/specs/10_TEST_AND_QUALITY.md

수행:
1. acceptance criteria를 테스트 ID로 매핑한다.
2. 허용·거부·다른 company·비활성·service account·AI acting user 권한을 검증한다.
3. 세션·CSRF·IDOR·파일·민감정보 로그·migration·outbox·복구를 공격 관점에서 검증한다.
4. 실제 실행 명령과 결과를 기록한다.
5. 결함을 Critical/High/Medium/Low로 분류한다.
6. Critical/High가 있으면 출시를 차단한다.
7. 수정 후 같은 테스트와 인접 회귀를 다시 실행한다.

출력:
- Scope
- Environment and Commit
- Test Matrix
- Passed
- Failed
- Security Findings
- Restore Evidence
- Release Decision
- Required Rechecks
```


# 작업 패키지별 프롬프트

## WP-PLT-001 실행 프롬프트

```text
당신은 Luminode ERP Platform의 Platform Backend Agent다.

작업 패키지: WP-PLT-001 — 저장소·모듈 경계 부트스트랩
기준 브랜치: main의 최신 통합 성공 커밋
작업 브랜치: feature/WP-PLT-001-repository-bootstrap
선행 작업: 없음

작업 시작 전에 실제 저장소에서 다음 문서를 순서대로 읽어라.
1. AGENTS.md
2. DECISIONS.md
3. docs/specs/00_MASTER_DESIGN.md
4. docs/specs/02_SYSTEM_ARCHITECTURE.md
5. docs/specs/05_API_AND_EVENT_CONTRACTS.md
6. docs/specs/08_SECURITY_AND_GOVERNANCE.md
7. docs/specs/10_TEST_AND_QUALITY.md
8. docs/specs/14_MASTER_IMPLEMENTATION_PLAN.md
9. docs/specs/15_PHASE_0_FOUNDATION_IMPLEMENTATION_PLAN.md
10. docs/work-packages/WP-PLT-001.md 또는 work_packages.yaml의 WP-PLT-001 항목

목표:
- Git 모노레포의 루트 규칙과 backend/web 최소 실행 경로를 만든다.
- 모듈 표준 구조와 공개 인터페이스 규칙을 문서화하고 자동 검사한다.
- 로컬과 CI에서 동일하게 실행되는 lint·type·test·build 명령을 제공한다.
- 설계 문서와 AGENTS 규칙을 저장소 기준선으로 편입한다.

비범위:
- 인증·조직·권한 등 업무 테이블 구현
- Docker Compose 서비스 구성
- 실제 업무 화면 또는 AI 기능

소유 경로:
- `README.md`, `AGENTS.md`, `DECISIONS.md`
- `pyproject.toml`, `package.json`, `pnpm-workspace.yaml`
- `.editorconfig`, `.gitignore`, `.env.example`, `.gitlab-ci.yml`
- `apps/backend/pyproject.toml`, `apps/backend/src/lep/**`의 부트스트랩 영역
- `apps/web/**`의 최소 앱 셸
- `packages/api-client`, `packages/ui`, 공통 config 패키지
- `scripts/check_boundaries.py`, `scripts/bootstrap.*`, `scripts/verify.*`
- `docs/architecture/module-boundaries.md`, `docs/work-packages/WP-PLT-001.md`

데이터베이스:
- 없음

API:
- `GET /health/live` — 프로세스 생존 확인

이벤트:
- 없음

권한:
- 없음. 인증 기능은 `WP-PLT-002`에서 시작한다.

반드시 지킬 순서:
1. 저장소 구조와 선행 작업의 공개 계약을 조사한다.
2. 첫 응답으로 아래 작업 시작 계약만 제출한다.
   - Work Package
   - Base Commit
   - In Scope / Out of Scope
   - Owned Paths / Tables
   - API / Event / Permission
   - State Transitions
   - Migration Plan
   - Tests
   - Shared Files Needed
   - Risks and Assumptions
3. 계약이 승인된 뒤 실패 테스트를 먼저 작성한다.
4. 아래 구현 절차를 안전한 최소 변경으로 수행한다.
   1. 승인된 설계 문서를 `docs/specs`에 복사하고 루트 문서의 읽기 순서를 고정한다.
   2. Python backend 패키지와 Next.js web workspace를 생성하되 샘플 업무 기능은 넣지 않는다.
   3. backend에 설정 로더, 구조화 로그 기본기, trace ID 생성기, 앱 팩토리와 `/health/live`를 만든다.
   4. 모듈 폴더 템플릿과 각 모듈의 `public.py` 또는 동등한 공개 경계를 정한다.
   5. 금지 import 예시 fixture를 포함한 모듈 경계 검사 스크립트를 작성한다.
   6. frontend에 최소 레이아웃과 API client 패키지 자리만 만들고 mock 업무 데이터는 넣지 않는다.
   7. backend lint/type/unit, frontend lint/type/build, boundary 검사, secret scan을 수행하는 CI 단계를 만든다.
   8. Linux와 Windows 개발자가 같은 결과를 얻도록 bootstrap/verify 스크립트를 각각 제공한다.
   9. 실행·검증·폴더 소유권을 README와 작업 패키지 문서에 기록한다.
5. 관련 설계·OpenAPI·migration·runbook을 갱신한다.
6. self-review 후 독립 리뷰를 요청한다.

필수 검증:
- `uv run pytest apps/backend/tests/architecture -q` — 허용 import는 통과하고 금지 fixture는 실패를 탐지한다.
- `uv run ruff check .` 및 타입 검사 — backend 정적 검사를 통과한다.
- `pnpm lint`, `pnpm typecheck`, `pnpm build` — web 최소 앱이 빌드된다.
- `python scripts/check_boundaries.py` — 모듈 경계 위반 0건이다.
- `scripts/verify.sh`와 `scripts/verify.ps1`의 명령 목록이 동일하다.

금지:
- 설계와 작업 패키지에 없는 기능 추가
- 다른 모듈 테이블 직접 INSERT/UPDATE/DELETE
- 권한·감사·상태 전이·멱등성 생략
- 실제 비밀·고객·직원 데이터 사용
- 이미 병합·적용된 migration 수정
- shared-file lock 없는 lockfile·공통 계약 변경
- 테스트 삭제·skip·환경 한정 우회
- 임시 admin bypass, CORS 전체 허용, debug token
- 완료 증거 없이 PASS 보고

인계 조건:
기본 브랜치 병합 후 `WP-OPS-001`이 Docker 이미지와 Compose를 추가한다. 루트 lockfile과 CI 구조 변경은 이후 Integration Agent 승인을 받는다.

완료 보고 형식:
Work Package:
Result: PASS / BLOCKED
Commits:
Files Changed:
Migrations:
API/Event Changes:
Permissions:
Tests Executed:
Results:
Security/Privacy Review:
Operational Notes:
Known Limitations:
Handoff:
```

## WP-OPS-001 실행 프롬프트

```text
당신은 Luminode ERP Platform의 DevOps Agent다.

작업 패키지: WP-OPS-001 — Docker Compose 개발·스테이징 기반
기준 브랜치: main의 최신 통합 성공 커밋
작업 브랜치: feature/WP-OPS-001-compose-foundation
선행 작업: WP-PLT-001

작업 시작 전에 실제 저장소에서 다음 문서를 순서대로 읽어라.
1. AGENTS.md
2. DECISIONS.md
3. docs/specs/00_MASTER_DESIGN.md
4. docs/specs/02_SYSTEM_ARCHITECTURE.md
5. docs/specs/05_API_AND_EVENT_CONTRACTS.md
6. docs/specs/08_SECURITY_AND_GOVERNANCE.md
7. docs/specs/10_TEST_AND_QUALITY.md
8. docs/specs/14_MASTER_IMPLEMENTATION_PLAN.md
9. docs/specs/15_PHASE_0_FOUNDATION_IMPLEMENTATION_PLAN.md
10. docs/work-packages/WP-OPS-001.md 또는 work_packages.yaml의 WP-OPS-001 항목

목표:
- 개발·스테이징에서 재현 가능한 컨테이너 실행 환경을 만든다.
- web, backend API, worker, scheduler, PostgreSQL, Redis, MinIO, reverse proxy를 구성한다.
- 서비스별 health check, 네트워크, 볼륨, 환경변수 템플릿과 이미지 고정 규칙을 만든다.

비범위:
- Prometheus/Grafana/Loki와 백업 자동화
- OpenSearch/Qdrant 활성화
- 운영 고가용성 또는 k3s

소유 경로:
- `apps/backend/Dockerfile`, `apps/web/Dockerfile`
- `infra/compose/compose.dev.yml`, `compose.staging.yml`, 공통 fragment
- `infra/edge/**`, `infra/scripts/wait-for-services.*`
- `.env.example`, `docs/runbooks/local-start.md`, `staging-deploy.md`

데이터베이스:
- PostgreSQL 초기 데이터베이스와 migration metadata만 생성

API:
- `GET /health/live`
- `GET /health/ready` — PostgreSQL·Redis 연결 상태를 포함하되 MinIO 일시 장애는 명시적으로 보고

이벤트:
- 없음

권한:
- 데이터 서비스는 애플리케이션 네트워크에서만 접근한다.

반드시 지킬 순서:
1. 저장소 구조와 선행 작업의 공개 계약을 조사한다.
2. 첫 응답으로 아래 작업 시작 계약만 제출한다.
   - Work Package
   - Base Commit
   - In Scope / Out of Scope
   - Owned Paths / Tables
   - API / Event / Permission
   - State Transitions
   - Migration Plan
   - Tests
   - Shared Files Needed
   - Risks and Assumptions
3. 계약이 승인된 뒤 실패 테스트를 먼저 작성한다.
4. 아래 구현 절차를 안전한 최소 변경으로 수행한다.
   1. backend와 web의 다단계 Dockerfile을 작성하고 root가 아닌 사용자로 실행한다.
   2. 개발 Compose에 PostgreSQL, Redis, MinIO, API, web, worker, scheduler를 정의한다.
   3. 스테이징 Compose는 이미지 태그 기반으로 구성하고 소스 bind mount를 제거한다.
   4. DB·Redis·MinIO는 host 전체에 공개하지 않고 개발 편의 포트도 `127.0.0.1`에만 바인딩한다.
   5. 서비스 시작 순서를 `depends_on`만 믿지 않고 실제 readiness 검사로 제어한다.
   6. named volume과 네트워크를 분리하고 데이터 볼륨 삭제 명령을 안전한 별도 스크립트로 둔다.
   7. 환경변수에 비밀 기본값을 넣지 않고 필요한 값·형식·생성 방법을 문서화한다.
   8. reverse proxy에서 web/API 경로, request size, timeout, 보안 헤더의 최소 기준을 설정한다.
   9. Compose 검증과 smoke test를 CI 또는 별도 운영 검증 명령에 추가한다.
5. 관련 설계·OpenAPI·migration·runbook을 갱신한다.
6. self-review 후 독립 리뷰를 요청한다.

필수 검증:
- `docker compose -f infra/compose/compose.dev.yml config`가 오류 없이 끝난다.
- 빈 환경에서 `up -d` 후 모든 필수 서비스가 healthy가 된다.
- API readiness가 DB/Redis 중단과 복구를 정확히 반영한다.
- DB·Redis·MinIO 포트가 허용된 인터페이스 외부에서 열리지 않는다.
- 컨테이너 재생성 후 named volume 데이터가 유지된다.
- 스테이징 manifest에 `latest` 태그와 평문 비밀이 없다.

금지:
- 설계와 작업 패키지에 없는 기능 추가
- 다른 모듈 테이블 직접 INSERT/UPDATE/DELETE
- 권한·감사·상태 전이·멱등성 생략
- 실제 비밀·고객·직원 데이터 사용
- 이미 병합·적용된 migration 수정
- shared-file lock 없는 lockfile·공통 계약 변경
- 테스트 삭제·skip·환경 한정 우회
- 임시 admin bypass, CORS 전체 허용, debug token
- 완료 증거 없이 PASS 보고

인계 조건:
`WP-PLT-002`는 이 환경에서 실제 migration과 세션 저장소를 사용한다. 관측성과 백업은 `WP-OPS-002`에서 확장한다.

완료 보고 형식:
Work Package:
Result: PASS / BLOCKED
Commits:
Files Changed:
Migrations:
API/Event Changes:
Permissions:
Tests Executed:
Results:
Security/Privacy Review:
Operational Notes:
Known Limitations:
Handoff:
```

## WP-PLT-002 실행 프롬프트

```text
당신은 Luminode ERP Platform의 Platform Backend Agent + Frontend Agent다.

작업 패키지: WP-PLT-002 — 인증·세션·MFA 기반
기준 브랜치: main의 최신 통합 성공 커밋
작업 브랜치: feature/WP-PLT-002-auth-session-mfa
선행 작업: WP-PLT-001, WP-OPS-001

작업 시작 전에 실제 저장소에서 다음 문서를 순서대로 읽어라.
1. AGENTS.md
2. DECISIONS.md
3. docs/specs/00_MASTER_DESIGN.md
4. docs/specs/02_SYSTEM_ARCHITECTURE.md
5. docs/specs/05_API_AND_EVENT_CONTRACTS.md
6. docs/specs/08_SECURITY_AND_GOVERNANCE.md
7. docs/specs/10_TEST_AND_QUALITY.md
8. docs/specs/14_MASTER_IMPLEMENTATION_PLAN.md
9. docs/specs/15_PHASE_0_FOUNDATION_IMPLEMENTATION_PLAN.md
10. docs/work-packages/WP-PLT-002.md 또는 work_packages.yaml의 WP-PLT-002 항목

목표:
- 사용자 로그인·로그아웃·세션 조회·세션 철회와 TOTP MFA를 구현한다.
- 비밀번호 정책, 로그인 잠금, 속도 제한, CSRF, 보안 이벤트와 초기 관리자 생성 절차를 구현한다.
- 웹 로그인·MFA challenge·세션 만료 UX를 제공한다.

비범위:
- 회사·부서·직원 관리
- 역할·권한 판정
- SSO·WebAuthn·외부 사용자 초대

소유 경로:
- `apps/backend/src/lep/modules/iam/**`의 auth 영역
- `apps/backend/migrations/*_iam_auth.py`
- `apps/backend/src/lep/api/middleware/auth.py`, `csrf.py`, `rate_limit.py`
- `apps/web/app/(auth)/**`, `apps/web/src/features/auth/**`
- `tests/security/auth/**`, `docs/runbooks/bootstrap-admin.md`

데이터베이스:
- `users`
- `user_credentials`
- `sessions`
- `mfa_factors`
- `security_events`

API:
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/mfa/challenge`
- `POST /api/v1/auth/logout`
- `GET /api/v1/auth/me`
- `GET /api/v1/auth/sessions`
- `DELETE /api/v1/auth/sessions/{session_id}`
- `POST /api/v1/auth/mfa/totp/enroll`
- `POST /api/v1/auth/mfa/totp/confirm`

이벤트:
- `iam.user_logged_in.v1`
- `iam.login_failed.v1`
- `iam.session_revoked.v1`
- `iam.mfa_enabled.v1`

권한:
- 로그인 전 endpoint와 본인 세션 endpoint만 제공한다. 관리자 권한 기능은 `WP-PLT-004` 이후 연결한다.

반드시 지킬 순서:
1. 저장소 구조와 선행 작업의 공개 계약을 조사한다.
2. 첫 응답으로 아래 작업 시작 계약만 제출한다.
   - Work Package
   - Base Commit
   - In Scope / Out of Scope
   - Owned Paths / Tables
   - API / Event / Permission
   - State Transitions
   - Migration Plan
   - Tests
   - Shared Files Needed
   - Risks and Assumptions
3. 계약이 승인된 뒤 실패 테스트를 먼저 작성한다.
4. 아래 구현 절차를 안전한 최소 변경으로 수행한다.
   1. 인증 상태와 세션 수명주기를 도메인 테스트로 먼저 작성한다.
   2. 비밀번호 hash는 Argon2id 계열 구현을 사용하고 원문·복구 가능 형태를 저장하지 않는다.
   3. 서버측 `sessions`를 authoritative record로 사용하고 Redis는 검증 캐시·속도 제한에 사용한다.
   4. HttpOnly·Secure·SameSite 정책의 세션 쿠키와 state-changing 요청의 CSRF 방어를 구현한다.
   5. 연속 실패 잠금과 IP/계정 조합 속도 제한을 구현하되 사용자 존재 여부를 응답으로 노출하지 않는다.
   6. TOTP seed는 암호화 저장하고 enrollment 확인 전 활성화하지 않는다.
   7. 사용자 비활성화 시 호출할 세션 일괄 철회 application interface를 제공한다.
   8. 초기 관리자에는 일시적 `bootstrap_admin` 표시를 부여하되 조직·권한 초기화에만 사용하고 `WP-PLT-004` 완료 시 역할 기반 관리자 권한으로 전환·폐기한다.
   9. 재실행 가능한 초기 관리자 생성 CLI를 만들고 비밀번호를 로그에 출력하지 않는다.
   10. 로그인·MFA·만료·강제 로그아웃 화면을 구현한다.
   11. 모든 성공·실패·철회를 security event와 trace로 기록한다.
5. 관련 설계·OpenAPI·migration·runbook을 갱신한다.
6. self-review 후 독립 리뷰를 요청한다.

필수 검증:
- 정상 로그인, 잘못된 비밀번호, 비활성 사용자, 잠금, 속도 제한을 검증한다.
- 세션 고정 공격 방지를 위해 로그인 전후 세션 식별자가 교체된다.
- 로그아웃·개별 세션 철회·사용자 비활성화 후 기존 세션이 즉시 거부된다.
- CSRF token이 없거나 origin 정책을 위반한 상태 변경 요청이 차단된다.
- MFA enrollment, 잘못된 코드, 재사용 코드, 복구 절차를 검증한다.
- 쿠키에 HttpOnly/Secure/SameSite가 적용되고 인증 토큰이 localStorage에 저장되지 않는다.
- 보안 로그에 비밀번호·TOTP seed·세션 원문이 없다.

금지:
- 설계와 작업 패키지에 없는 기능 추가
- 다른 모듈 테이블 직접 INSERT/UPDATE/DELETE
- 권한·감사·상태 전이·멱등성 생략
- 실제 비밀·고객·직원 데이터 사용
- 이미 병합·적용된 migration 수정
- shared-file lock 없는 lockfile·공통 계약 변경
- 테스트 삭제·skip·환경 한정 우회
- 임시 admin bypass, CORS 전체 허용, debug token
- 완료 증거 없이 PASS 보고

인계 조건:
`WP-PLT-003`은 `users`를 회사·직원과 연결하고, `WP-PLT-004`는 인증 주체에 역할·범위를 부여한다.

완료 보고 형식:
Work Package:
Result: PASS / BLOCKED
Commits:
Files Changed:
Migrations:
API/Event Changes:
Permissions:
Tests Executed:
Results:
Security/Privacy Review:
Operational Notes:
Known Limitations:
Handoff:
```

## WP-PLT-003 실행 프롬프트

```text
당신은 Luminode ERP Platform의 Platform Backend Agent + Frontend Agent다.

작업 패키지: WP-PLT-003 — 회사·부서·직원·사용자 관리
기준 브랜치: main의 최신 통합 성공 커밋
작업 브랜치: feature/WP-PLT-003-organization-users
선행 작업: WP-PLT-002

작업 시작 전에 실제 저장소에서 다음 문서를 순서대로 읽어라.
1. AGENTS.md
2. DECISIONS.md
3. docs/specs/00_MASTER_DESIGN.md
4. docs/specs/02_SYSTEM_ARCHITECTURE.md
5. docs/specs/05_API_AND_EVENT_CONTRACTS.md
6. docs/specs/08_SECURITY_AND_GOVERNANCE.md
7. docs/specs/10_TEST_AND_QUALITY.md
8. docs/specs/14_MASTER_IMPLEMENTATION_PLAN.md
9. docs/specs/15_PHASE_0_FOUNDATION_IMPLEMENTATION_PLAN.md
10. docs/work-packages/WP-PLT-003.md 또는 work_packages.yaml의 WP-PLT-003 항목

목표:
- 회사·부서 계층·직원 기본 프로필·사용자 계정 연결을 관리한다.
- 입사·재직·휴직·퇴사 상태와 계정 활성화/비활성화를 분리한다.
- 관리자용 조직·사용자 화면과 안전한 퇴사 이력 보존을 제공한다.

비범위:
- 민감 인사정보·급여·평가
- 역할·권한 설정
- 휴가·근태

소유 경로:
- `apps/backend/src/lep/modules/iam/**`의 organization 영역
- `apps/backend/src/lep/modules/hr_core/**`
- `apps/backend/migrations/*_organization.py`
- `apps/web/app/(erp)/admin/organization/**`
- `apps/web/src/features/organization/**`

데이터베이스:
- `companies`
- `departments`
- `positions`
- `job_titles`
- `employment_types`
- `employees`
- `user_employee_links` 또는 동등한 명시적 연결 구조

API:
- `GET/POST /api/v1/companies`
- `GET/POST/PATCH /api/v1/departments`
- `GET/POST/PATCH /api/v1/employees`
- `POST /api/v1/employees/{id}/transitions/{action}`
- `GET/POST/PATCH /api/v1/users`
- `POST /api/v1/users/{id}/activate`
- `POST /api/v1/users/{id}/deactivate`

이벤트:
- `hr.employee_created.v1`
- `hr.employee_status_changed.v1`
- `iam.user_activated.v1`
- `iam.user_deactivated.v1`

권한:
- `iam.organization.read`
- `iam.organization.manage`
- `iam.user.read`
- `iam.user.manage`
- `hr.employee.read_basic`
- `hr.employee.manage_basic`
- RBAC 전 단계에서는 위 endpoint를 feature flag와 `bootstrap_admin`에만 제한하며 `WP-PLT-004` 병합 전 일반 사용자에게 활성화하지 않는다.

반드시 지킬 순서:
1. 저장소 구조와 선행 작업의 공개 계약을 조사한다.
2. 첫 응답으로 아래 작업 시작 계약만 제출한다.
   - Work Package
   - Base Commit
   - In Scope / Out of Scope
   - Owned Paths / Tables
   - API / Event / Permission
   - State Transitions
   - Migration Plan
   - Tests
   - Shared Files Needed
   - Risks and Assumptions
3. 계약이 승인된 뒤 실패 테스트를 먼저 작성한다.
4. 아래 구현 절차를 안전한 최소 변경으로 수행한다.
   1. 부서 순환 참조, 동일 회사 내 코드 중복, 직원 상태 전이 규칙을 테스트로 고정한다.
   2. 단일 회사 운영을 기본으로 하되 모든 조직 데이터에 `company_id`를 유지한다.
   3. 부서 이동·직책 변경·퇴사는 과거 이력을 보존하는 상태 전이로 구현한다.
   4. 사용자와 직원은 1:1 기본이지만 서비스 계정·미연결 직원이 가능하도록 분리한다.
   5. 퇴사 전환 시 세션 철회 interface를 호출하고 이후 로그인과 업무 배정을 막는다.
   6. 조직 트리, 직원 목록·상세, 사용자 연결·비활성화 화면을 구현한다.
   7. 민감 인사 필드는 이 단계에 넣지 않고 Phase 4 전용 테이블로 남긴다.
   8. 변경 전후와 사유를 감사에 남길 수 있도록 command metadata를 준비한다.
5. 관련 설계·OpenAPI·migration·runbook을 갱신한다.
6. self-review 후 독립 리뷰를 요청한다.

필수 검증:
- 부서 트리 생성·이동·비활성화와 순환 참조 차단을 검증한다.
- 직원과 사용자 연결·분리, 계정 비활성화, 퇴사 이력 보존을 검증한다.
- 다른 회사 식별자를 사용한 객체 접근이 차단된다.
- 퇴사 후 세션과 로그인, 신규 업무 배정 가능 여부가 차단된다.
- 직원 삭제 대신 상태 전이가 사용되고 FK 이력이 유지된다.
- 조직 화면의 loading/empty/error/forbidden 상태를 검증한다.

금지:
- 설계와 작업 패키지에 없는 기능 추가
- 다른 모듈 테이블 직접 INSERT/UPDATE/DELETE
- 권한·감사·상태 전이·멱등성 생략
- 실제 비밀·고객·직원 데이터 사용
- 이미 병합·적용된 migration 수정
- shared-file lock 없는 lockfile·공통 계약 변경
- 테스트 삭제·skip·환경 한정 우회
- 임시 admin bypass, CORS 전체 허용, debug token
- 완료 증거 없이 PASS 보고

인계 조건:
`WP-PLT-004`가 조직 엔터티를 scope 계산에 사용한다. Phase 4는 별도 HR 민감 영역을 추가한다.

완료 보고 형식:
Work Package:
Result: PASS / BLOCKED
Commits:
Files Changed:
Migrations:
API/Event Changes:
Permissions:
Tests Executed:
Results:
Security/Privacy Review:
Operational Notes:
Known Limitations:
Handoff:
```

## WP-UI-001 실행 프롬프트

```text
당신은 Luminode ERP Platform의 Frontend/UX Agent다.

작업 패키지: WP-UI-001 — 디자인 시스템·전역 레이아웃
기준 브랜치: main의 최신 통합 성공 커밋
작업 브랜치: feature/WP-UI-001-design-system-shell
선행 작업: WP-PLT-001, WP-PLT-002

작업 시작 전에 실제 저장소에서 다음 문서를 순서대로 읽어라.
1. AGENTS.md
2. DECISIONS.md
3. docs/specs/00_MASTER_DESIGN.md
4. docs/specs/02_SYSTEM_ARCHITECTURE.md
5. docs/specs/05_API_AND_EVENT_CONTRACTS.md
6. docs/specs/08_SECURITY_AND_GOVERNANCE.md
7. docs/specs/10_TEST_AND_QUALITY.md
8. docs/specs/14_MASTER_IMPLEMENTATION_PLAN.md
9. docs/specs/15_PHASE_0_FOUNDATION_IMPLEMENTATION_PLAN.md
10. docs/work-packages/WP-UI-001.md 또는 work_packages.yaml의 WP-UI-001 항목

목표:
- ERP 전역 앱 셸, 내비게이션, 디자인 토큰과 공통 화면 상태를 만든다.
- 인증 세션과 권한 정보를 받아 메뉴·행동을 표시하는 기반을 만든다.
- 접근성·반응형·한국어 날짜/금액 표시 기준을 제공한다.

비범위:
- 프로젝트·CRM 등 도메인 화면
- 서버 권한 판정
- 브랜드 마케팅 사이트

소유 경로:
- `packages/ui/**`
- `packages/tsconfig/**`, `packages/eslint-config/**`
- `apps/web/app/(erp)/layout.tsx`
- `apps/web/src/widgets/app-shell/**`
- `apps/web/src/shared/auth/**`, `locale/**`, `states/**`
- `apps/web/app/dev/components/**`의 개발 전용 컴포넌트 갤러리

데이터베이스:
- 없음

API:
- `GET /api/v1/auth/me`를 소비한다.

이벤트:
- 없음

권한:
- 권한 기반 표시 helper를 제공하되 서버 권한 검사를 대체하지 않는다.

반드시 지킬 순서:
1. 저장소 구조와 선행 작업의 공개 계약을 조사한다.
2. 첫 응답으로 아래 작업 시작 계약만 제출한다.
   - Work Package
   - Base Commit
   - In Scope / Out of Scope
   - Owned Paths / Tables
   - API / Event / Permission
   - State Transitions
   - Migration Plan
   - Tests
   - Shared Files Needed
   - Risks and Assumptions
3. 계약이 승인된 뒤 실패 테스트를 먼저 작성한다.
4. 아래 구현 절차를 안전한 최소 변경으로 수행한다.
   1. 색상에 의존하지 않는 상태 토큰, 간격, typography, elevation, focus 기준을 정의한다.
   2. Button, Input, Select, Dialog, Drawer, Table, Tabs, Badge, Toast, Skeleton, EmptyState, ErrorState, ForbiddenState, ConflictState를 만든다.
   3. 좌측 내비게이션, 상단바, 모바일 drawer, 우측 컨텍스트 패널을 포함한 앱 셸을 만든다.
   4. 세션 만료와 강제 로그아웃을 전역적으로 처리한다.
   5. 한국어 날짜·시간·KRW 포맷 유틸리티를 만들고 저장 시간과 표시 시간의 차이를 테스트한다.
   6. 모든 공통 컴포넌트에 키보드 focus와 accessible name을 제공한다.
   7. 개발 전용 갤러리에서 각 컴포넌트의 loading/disabled/error 상태를 확인하게 한다.
   8. 도메인 메뉴는 feature flag와 permission descriptor로 등록하는 방식으로 만든다.
5. 관련 설계·OpenAPI·migration·runbook을 갱신한다.
6. self-review 후 독립 리뷰를 요청한다.

필수 검증:
- 키보드만으로 전역 메뉴·다이얼로그·폼을 조작한다.
- 좁은 화면에서 메뉴가 겹치지 않고 핵심 행동이 유지된다.
- 상태가 색상만으로 구분되지 않는다.
- 인증 만료와 forbidden 응답의 전역 처리 흐름을 검증한다.
- 컴포넌트 단위 접근성 검사와 핵심 앱 셸 Playwright smoke를 통과한다.
- API 호출이 페이지 내부에 중복 작성되지 않고 generated client 경로를 사용한다.

금지:
- 설계와 작업 패키지에 없는 기능 추가
- 다른 모듈 테이블 직접 INSERT/UPDATE/DELETE
- 권한·감사·상태 전이·멱등성 생략
- 실제 비밀·고객·직원 데이터 사용
- 이미 병합·적용된 migration 수정
- shared-file lock 없는 lockfile·공통 계약 변경
- 테스트 삭제·skip·환경 한정 우회
- 임시 admin bypass, CORS 전체 허용, debug token
- 완료 증거 없이 PASS 보고

인계 조건:
Phase 1 이후 모든 Frontend Agent는 `packages/ui`의 기준을 재사용한다. 공통 토큰 변경은 UI owner 승인이 필요하다.

완료 보고 형식:
Work Package:
Result: PASS / BLOCKED
Commits:
Files Changed:
Migrations:
API/Event Changes:
Permissions:
Tests Executed:
Results:
Security/Privacy Review:
Operational Notes:
Known Limitations:
Handoff:
```

## WP-PLT-004 실행 프롬프트

```text
당신은 Luminode ERP Platform의 Platform Backend Agent + QA·Security Agent다.

작업 패키지: WP-PLT-004 — RBAC·범위 권한 엔진
기준 브랜치: main의 최신 통합 성공 커밋
작업 브랜치: feature/WP-PLT-004-rbac-scope-engine
선행 작업: WP-PLT-002, WP-PLT-003

작업 시작 전에 실제 저장소에서 다음 문서를 순서대로 읽어라.
1. AGENTS.md
2. DECISIONS.md
3. docs/specs/00_MASTER_DESIGN.md
4. docs/specs/02_SYSTEM_ARCHITECTURE.md
5. docs/specs/05_API_AND_EVENT_CONTRACTS.md
6. docs/specs/08_SECURITY_AND_GOVERNANCE.md
7. docs/specs/10_TEST_AND_QUALITY.md
8. docs/specs/14_MASTER_IMPLEMENTATION_PLAN.md
9. docs/specs/15_PHASE_0_FOUNDATION_IMPLEMENTATION_PLAN.md
10. docs/work-packages/WP-PLT-004.md 또는 work_packages.yaml의 WP-PLT-004 항목

목표:
- permission catalog, 역할, 사용자 역할 할당과 company/department/project/self 범위를 구현한다.
- API object-level 권한 검사와 관리자용 권한 시뮬레이터를 제공한다.
- 외부 사용자·AI acting user가 확장 가능한 정책 인터페이스를 만든다.

비범위:
- 프로젝트 멤버 권한의 실제 구현
- 복잡한 정책 언어 또는 범용 ABAC 엔진
- SSO 그룹 동기화

소유 경로:
- `apps/backend/src/lep/modules/iam/domain/permissions.py`
- `apps/backend/src/lep/modules/iam/application/authorization/**`
- `apps/backend/src/lep/modules/iam/infrastructure/**`
- `apps/backend/src/lep/api/dependencies/authorization.py`
- `apps/web/app/(erp)/admin/roles/**`
- `tests/security/authorization/**`

데이터베이스:
- `roles`
- `permissions`
- `role_permissions`
- `user_role_assignments`
- `authorization_policy_versions` 또는 동등한 정책 버전 기록

API:
- `GET/POST/PATCH /api/v1/roles`
- `GET /api/v1/permissions`
- `POST/DELETE /api/v1/users/{id}/role-assignments`
- `POST /api/v1/authorization/simulate`

이벤트:
- `iam.role_changed.v1`
- `iam.role_assignment_changed.v1`
- `iam.permission_catalog_changed.v1`

권한:
- `iam.role.read`
- `iam.role.manage`
- `iam.permission.simulate`
- `audit.authorization.read`

반드시 지킬 순서:
1. 저장소 구조와 선행 작업의 공개 계약을 조사한다.
2. 첫 응답으로 아래 작업 시작 계약만 제출한다.
   - Work Package
   - Base Commit
   - In Scope / Out of Scope
   - Owned Paths / Tables
   - API / Event / Permission
   - State Transitions
   - Migration Plan
   - Tests
   - Shared Files Needed
   - Risks and Assumptions
3. 계약이 승인된 뒤 실패 테스트를 먼저 작성한다.
4. 아래 구현 절차를 안전한 최소 변경으로 수행한다.
   1. 기능 permission과 data scope를 분리한 판정 결과 모델을 만든다.
   2. company/department/self resolver를 구현하고 project resolver는 공개 port만 정의한다.
   3. API dependency가 action·resource·object를 받아 object-level 검사를 강제하도록 만든다.
   4. 초기 `bootstrap_admin` 사용자를 승인된 시스템 관리자 역할로 이관하고 임시 bootstrap 경로를 비활성화한다.
   5. 기본 역할을 seed하되 role 이름을 코드에 권한 판단 조건으로 사용하지 않는다.
   6. 권한 캐시는 정책 버전과 사용자 assignment 변경 시 즉시 무효화한다.
   7. 관리자 시뮬레이터는 결과뿐 아니라 적용 역할·scope·거부 이유를 설명한다.
   8. 권한 변경, 시뮬레이션, 거부를 감사·보안 로그와 연결한다.
   9. AI acting user와 외부 사용자에 대해 원 사용자보다 넓은 권한을 만들 수 없게 인터페이스를 제한한다.
5. 관련 설계·OpenAPI·migration·runbook을 갱신한다.
6. self-review 후 독립 리뷰를 요청한다.

필수 검증:
- 허용 역할, 권한 없음, 다른 부서, self 제한, 비활성 사용자, service account를 검증한다.
- 목록 필터와 상세 object check가 동일한 결과를 낸다.
- role 이름 변경이 권한 로직에 영향을 주지 않는다.
- 권한 변경 후 기존 캐시가 즉시 무효화된다.
- 시뮬레이터가 실제 API 권한 판정과 동일한 결과를 낸다.
- 다른 company 객체와 추측 가능한 UUID를 사용한 IDOR이 차단된다.
- `WP-PLT-004` 완료 후 `bootstrap_admin` 임시 경로만으로 조직·권한 API를 호출할 수 없다.

금지:
- 설계와 작업 패키지에 없는 기능 추가
- 다른 모듈 테이블 직접 INSERT/UPDATE/DELETE
- 권한·감사·상태 전이·멱등성 생략
- 실제 비밀·고객·직원 데이터 사용
- 이미 병합·적용된 migration 수정
- shared-file lock 없는 lockfile·공통 계약 변경
- 테스트 삭제·skip·환경 한정 우회
- 임시 admin bypass, CORS 전체 허용, debug token
- 완료 증거 없이 PASS 보고

인계 조건:
모든 이후 모듈은 permission code와 scope resolver를 등록한다. 권한 우회용 직접 repository 호출을 금지한다.

완료 보고 형식:
Work Package:
Result: PASS / BLOCKED
Commits:
Files Changed:
Migrations:
API/Event Changes:
Permissions:
Tests Executed:
Results:
Security/Privacy Review:
Operational Notes:
Known Limitations:
Handoff:
```

## WP-PLT-005 실행 프롬프트

```text
당신은 Luminode ERP Platform의 Platform Backend Agent다.

작업 패키지: WP-PLT-005 — 감사 로그·활동 로그·Outbox
기준 브랜치: main의 최신 통합 성공 커밋
작업 브랜치: feature/WP-PLT-005-audit-outbox
선행 작업: WP-PLT-004

작업 시작 전에 실제 저장소에서 다음 문서를 순서대로 읽어라.
1. AGENTS.md
2. DECISIONS.md
3. docs/specs/00_MASTER_DESIGN.md
4. docs/specs/02_SYSTEM_ARCHITECTURE.md
5. docs/specs/05_API_AND_EVENT_CONTRACTS.md
6. docs/specs/08_SECURITY_AND_GOVERNANCE.md
7. docs/specs/10_TEST_AND_QUALITY.md
8. docs/specs/14_MASTER_IMPLEMENTATION_PLAN.md
9. docs/specs/15_PHASE_0_FOUNDATION_IMPLEMENTATION_PLAN.md
10. docs/work-packages/WP-PLT-005.md 또는 work_packages.yaml의 WP-PLT-005 항목

목표:
- 중요 command의 actor·before·after·reason·trace를 남기는 감사 체계를 만든다.
- 사용자 활동 타임라인과 트랜잭션 outbox·멱등 소비 기반을 만든다.
- 요청 trace와 RFC 7807 오류 계약을 공통화한다.

비범위:
- 도메인별 전체 이벤트 카탈로그 구현
- 외부 message broker
- SIEM 연동

소유 경로:
- `apps/backend/src/lep/common/audit/**`
- `apps/backend/src/lep/common/events/**`
- `apps/backend/src/lep/common/idempotency/**`
- `apps/backend/src/lep/api/middleware/trace.py`
- `apps/backend/src/lep/workers/outbox/**`
- `tests/contract/events/**`, `tests/security/audit/**`

데이터베이스:
- `audit_logs`
- `activity_logs`
- `outbox_events`
- `event_consumptions`
- `idempotency_records`

API:
- `GET /api/v1/audit-logs`
- `GET /api/v1/activities`
- `POST` command endpoint용 `Idempotency-Key` 공통 처리

이벤트:
- `core.audit_recorded.v1`은 외부 발행하지 않고 내부 운영 이벤트로 제한
- outbox envelope 표준을 모든 도메인 이벤트에 적용

권한:
- `audit.log.read`
- `activity.read`
- 감사 로그 update/delete permission은 애플리케이션에 제공하지 않는다.

반드시 지킬 순서:
1. 저장소 구조와 선행 작업의 공개 계약을 조사한다.
2. 첫 응답으로 아래 작업 시작 계약만 제출한다.
   - Work Package
   - Base Commit
   - In Scope / Out of Scope
   - Owned Paths / Tables
   - API / Event / Permission
   - State Transitions
   - Migration Plan
   - Tests
   - Shared Files Needed
   - Risks and Assumptions
3. 계약이 승인된 뒤 실패 테스트를 먼저 작성한다.
4. 아래 구현 절차를 안전한 최소 변경으로 수행한다.
   1. command context에 actor_user_id, acting_service_id, company_id, reason, trace_id를 표준화한다.
   2. before/after 전체 원문이 아니라 정책에 따른 diff와 마스킹된 snapshot을 저장한다.
   3. 같은 DB transaction에서 업무 변경과 outbox insert가 함께 commit되도록 helper를 만든다.
   4. worker가 `SKIP LOCKED` 또는 동등한 안전한 claim 방식으로 outbox를 처리한다.
   5. consumer는 event_id 기준으로 중복 실행을 방지하고 실패를 재시도·보관한다.
   6. idempotency record가 요청 hash와 결과 resource id를 저장하고 다른 payload 재사용을 거부한다.
   7. 감사 테이블에 애플리케이션 역할의 UPDATE/DELETE를 허용하지 않는다.
   8. Problem Details 응답에 trace ID, 안정된 error code, 안전한 detail을 포함한다.
   9. 관리자 감사 조회와 사용자 활동 타임라인 조회 모델을 분리한다.
5. 관련 설계·OpenAPI·migration·runbook을 갱신한다.
6. self-review 후 독립 리뷰를 요청한다.

필수 검증:
- 업무 변경과 outbox가 함께 commit 또는 rollback된다.
- 같은 idempotency key와 같은 payload는 같은 결과를, 다른 payload는 충돌을 반환한다.
- outbox consumer 재실행이 중복 notification 또는 상태 변경을 만들지 않는다.
- 일반 앱 권한으로 audit row 수정·삭제가 실패한다.
- 민감 필드가 before/after와 오류 로그에 남지 않는다.
- trace ID가 API→DB audit→outbox→worker 로그까지 유지된다.

금지:
- 설계와 작업 패키지에 없는 기능 추가
- 다른 모듈 테이블 직접 INSERT/UPDATE/DELETE
- 권한·감사·상태 전이·멱등성 생략
- 실제 비밀·고객·직원 데이터 사용
- 이미 병합·적용된 migration 수정
- shared-file lock 없는 lockfile·공통 계약 변경
- 테스트 삭제·skip·환경 한정 우회
- 임시 admin bypass, CORS 전체 허용, debug token
- 완료 증거 없이 PASS 보고

인계 조건:
`WP-PLT-006`, `WP-PLT-007`과 모든 업무 모듈은 이 command/audit/outbox 기반을 의무적으로 사용한다.

완료 보고 형식:
Work Package:
Result: PASS / BLOCKED
Commits:
Files Changed:
Migrations:
API/Event Changes:
Permissions:
Tests Executed:
Results:
Security/Privacy Review:
Operational Notes:
Known Limitations:
Handoff:
```

## WP-PLT-006 실행 프롬프트

```text
당신은 Luminode ERP Platform의 DMS Agent + QA·Security Agent다.

작업 패키지: WP-PLT-006 — 파일 업로드·검사·MinIO 기반
기준 브랜치: main의 최신 통합 성공 커밋
작업 브랜치: feature/WP-PLT-006-secure-file-storage
선행 작업: WP-OPS-001, WP-PLT-004, WP-PLT-005

작업 시작 전에 실제 저장소에서 다음 문서를 순서대로 읽어라.
1. AGENTS.md
2. DECISIONS.md
3. docs/specs/00_MASTER_DESIGN.md
4. docs/specs/02_SYSTEM_ARCHITECTURE.md
5. docs/specs/05_API_AND_EVENT_CONTRACTS.md
6. docs/specs/08_SECURITY_AND_GOVERNANCE.md
7. docs/specs/10_TEST_AND_QUALITY.md
8. docs/specs/14_MASTER_IMPLEMENTATION_PLAN.md
9. docs/specs/15_PHASE_0_FOUNDATION_IMPLEMENTATION_PLAN.md
10. docs/work-packages/WP-PLT-006.md 또는 work_packages.yaml의 WP-PLT-006 항목

목표:
- 분할 업로드, 체크섬, 악성코드 검사, 격리, 권한 기반 다운로드를 구현한다.
- MinIO object key와 사용자 파일명을 분리하고 파일 상태 머신을 제공한다.
- 향후 문서·증빙·계약·AI 원문이 재사용할 file object 기반을 만든다.

비범위:
- 문서 폴더·버전·산출물
- ZIP 내부 추출·OCR·RAG
- 외부 공개 링크

소유 경로:
- `apps/backend/src/lep/modules/dms_core/**`
- `apps/backend/src/lep/workers/documents/scan.py`
- `apps/backend/migrations/*_file_objects.py`
- `apps/web/src/features/file-upload/**`
- `infra/compose`의 antivirus scanner 서비스
- `tests/security/files/**`

데이터베이스:
- `file_objects`
- `file_upload_sessions`
- `file_upload_parts`
- `file_scan_results`

API:
- `POST /api/v1/files/upload-sessions`
- `POST /api/v1/files/upload-sessions/{id}/parts`
- `POST /api/v1/files/upload-sessions/{id}/complete`
- `GET /api/v1/files/{id}`
- `GET /api/v1/files/{id}/download`
- `DELETE /api/v1/files/upload-sessions/{id}`

이벤트:
- `dms.file_uploaded.v1`
- `dms.file_scan_completed.v1`
- `dms.file_ready.v1`
- `dms.file_rejected.v1`

권한:
- `dms.file.upload`
- `dms.file.read`
- `dms.file.download`
- `dms.file.quarantine.manage`

반드시 지킬 순서:
1. 저장소 구조와 선행 작업의 공개 계약을 조사한다.
2. 첫 응답으로 아래 작업 시작 계약만 제출한다.
   - Work Package
   - Base Commit
   - In Scope / Out of Scope
   - Owned Paths / Tables
   - API / Event / Permission
   - State Transitions
   - Migration Plan
   - Tests
   - Shared Files Needed
   - Risks and Assumptions
3. 계약이 승인된 뒤 실패 테스트를 먼저 작성한다.
4. 아래 구현 절차를 안전한 최소 변경으로 수행한다.
   1. 파일 상태 `PENDING_UPLOAD→UPLOADED→SCANNING→READY`와 실패/격리 전이를 테스트로 고정한다.
   2. object key는 서버가 생성하고 파일명·경로·Content-Type을 신뢰하지 않는다.
   3. multipart upload session의 만료, part size, 총 크기, checksum을 검증한다.
   4. 업로드 완료 직후 파일을 비공개 격리 bucket에 두고 검사 성공 전 다운로드를 금지한다.
   5. antivirus worker는 timeout·재시도·실패 보관을 지원하고 검사 엔진 장애를 READY로 처리하지 않는다.
   6. 다운로드는 원본 권한 resolver를 호출한 뒤 짧은 수명의 서명 URL 또는 stream을 제공한다.
   7. 브라우저 uploader에 재시도, 진행률, 취소, 검사 중, 거부 상태를 제공한다.
   8. 파일 확장자와 MIME 불일치, 경로 문자, 초대형 파일, 중복 checksum 정책을 정의한다.
   9. 만료된 upload session과 orphan object를 안전하게 정리하는 scheduler 작업을 만든다.
5. 관련 설계·OpenAPI·migration·runbook을 갱신한다.
6. self-review 후 독립 리뷰를 요청한다.

필수 검증:
- 정상 multipart 업로드와 checksum 불일치·part 누락을 검증한다.
- 표준 antivirus test artifact가 REJECTED/QUARANTINED가 되고 다운로드되지 않는다.
- 검사 엔진 중단 시 파일이 READY가 되지 않고 재시도된다.
- 다른 사용자·회사·권한 없는 service account의 다운로드가 차단된다.
- 파일명 경로 순회, MIME spoofing, oversized upload, presigned URL 만료를 검증한다.
- MinIO object와 DB metadata가 불일치할 때 복구 가능한 오류로 보고된다.

금지:
- 설계와 작업 패키지에 없는 기능 추가
- 다른 모듈 테이블 직접 INSERT/UPDATE/DELETE
- 권한·감사·상태 전이·멱등성 생략
- 실제 비밀·고객·직원 데이터 사용
- 이미 병합·적용된 migration 수정
- shared-file lock 없는 lockfile·공통 계약 변경
- 테스트 삭제·skip·환경 한정 우회
- 임시 admin bypass, CORS 전체 허용, debug token
- 완료 증거 없이 PASS 보고

인계 조건:
Phase 1 `WP-DMS-001`은 `file_objects`를 문서 버전에 연결한다. 다른 모듈은 binary를 직접 저장하지 않는다.

완료 보고 형식:
Work Package:
Result: PASS / BLOCKED
Commits:
Files Changed:
Migrations:
API/Event Changes:
Permissions:
Tests Executed:
Results:
Security/Privacy Review:
Operational Notes:
Known Limitations:
Handoff:
```

## WP-PLT-007 실행 프롬프트

```text
당신은 Luminode ERP Platform의 Platform Backend Agent + Frontend Agent다.

작업 패키지: WP-PLT-007 — 댓글·멘션·알림 기반
기준 브랜치: main의 최신 통합 성공 커밋
작업 브랜치: feature/WP-PLT-007-collaboration-notifications
선행 작업: WP-PLT-004, WP-PLT-005

작업 시작 전에 실제 저장소에서 다음 문서를 순서대로 읽어라.
1. AGENTS.md
2. DECISIONS.md
3. docs/specs/00_MASTER_DESIGN.md
4. docs/specs/02_SYSTEM_ARCHITECTURE.md
5. docs/specs/05_API_AND_EVENT_CONTRACTS.md
6. docs/specs/08_SECURITY_AND_GOVERNANCE.md
7. docs/specs/10_TEST_AND_QUALITY.md
8. docs/specs/14_MASTER_IMPLEMENTATION_PLAN.md
9. docs/specs/15_PHASE_0_FOUNDATION_IMPLEMENTATION_PLAN.md
10. docs/work-packages/WP-PLT-007.md 또는 work_packages.yaml의 WP-PLT-007 항목

목표:
- 모든 업무 엔터티가 재사용할 댓글·답글·멘션·구독·인앱 알림 기반을 만든다.
- 권한 resolver를 통해 대상 엔터티 접근 권한을 확인한다.
- 중복 억제, 읽음 처리, 비동기 전달 실패 격리를 구현한다.

비범위:
- 실시간 사내 메신저
- SMS·카카오 등 다채널 연동
- 도메인별 고급 알림 규칙

소유 경로:
- `apps/backend/src/lep/modules/collab/**`
- `apps/backend/src/lep/workers/notifications/**`
- `apps/backend/migrations/*_collaboration.py`
- `apps/web/src/features/comments/**`, `notifications/**`
- `apps/web/src/widgets/notification-center/**`

데이터베이스:
- `comments`
- `comment_mentions`
- `attachments`
- `subscriptions`
- `notifications`
- `notification_deliveries`

API:
- `GET/POST /api/v1/entities/{entity_type}/{entity_id}/comments`
- `PATCH/DELETE /api/v1/comments/{id}`
- `GET /api/v1/notifications`
- `POST /api/v1/notifications/{id}/read`
- `POST /api/v1/notifications/read-all`
- `PUT /api/v1/subscriptions/{entity_type}/{entity_id}`

이벤트:
- `collab.comment_created.v1`
- `collab.user_mentioned.v1`
- `collab.notification_created.v1`
- `collab.notification_delivery_failed.v1`

권한:
- `collab.comment.create`
- `collab.comment.edit_own`
- `collab.comment.moderate`
- `collab.notification.read_self`

반드시 지킬 순서:
1. 저장소 구조와 선행 작업의 공개 계약을 조사한다.
2. 첫 응답으로 아래 작업 시작 계약만 제출한다.
   - Work Package
   - Base Commit
   - In Scope / Out of Scope
   - Owned Paths / Tables
   - API / Event / Permission
   - State Transitions
   - Migration Plan
   - Tests
   - Shared Files Needed
   - Risks and Assumptions
3. 계약이 승인된 뒤 실패 테스트를 먼저 작성한다.
4. 아래 구현 절차를 안전한 최소 변경으로 수행한다.
   1. generic target reference는 허용된 entity type registry와 권한 resolver를 통과하게 한다.
   2. 댓글 수정 가능 기간·본인 수정·관리자 숨김·삭제 대신 tombstone 정책을 정의한다.
   3. 멘션 대상은 같은 company와 접근 가능한 사용자만 허용한다.
   4. 알림은 `(recipient, type, object, dedupe window)` 기준으로 중복을 억제한다.
   5. 인앱 알림 생성과 이메일 전달을 분리하여 이메일 실패가 transaction을 막지 않게 한다.
   6. 댓글 첨부는 `file_objects` READY 상태만 연결한다.
   7. 댓글 패널과 알림 센터에 loading/empty/error/읽음/실패 상태를 구현한다.
   8. 알림 payload에 민감 원문을 과도하게 넣지 않고 대상 조회 시 권한을 다시 검사한다.
5. 관련 설계·OpenAPI·migration·runbook을 갱신한다.
6. self-review 후 독립 리뷰를 요청한다.

필수 검증:
- 권한 없는 대상에 댓글·조회·멘션을 할 수 없다.
- 다른 회사 사용자 또는 비활성 사용자를 멘션할 수 없다.
- 동일 이벤트 재처리로 중복 알림이 생성되지 않는다.
- 이메일 worker 실패에도 댓글과 인앱 알림은 유지된다.
- 댓글 수정·숨김·tombstone의 감사 이력이 남는다.
- 알림 링크 대상 권한이 사라지면 상세 정보가 노출되지 않는다.

금지:
- 설계와 작업 패키지에 없는 기능 추가
- 다른 모듈 테이블 직접 INSERT/UPDATE/DELETE
- 권한·감사·상태 전이·멱등성 생략
- 실제 비밀·고객·직원 데이터 사용
- 이미 병합·적용된 migration 수정
- shared-file lock 없는 lockfile·공통 계약 변경
- 테스트 삭제·skip·환경 한정 우회
- 임시 admin bypass, CORS 전체 허용, debug token
- 완료 증거 없이 PASS 보고

인계 조건:
Phase 1 프로젝트·회의·문서·결재가 댓글과 알림을 공통 서비스로 사용한다.

완료 보고 형식:
Work Package:
Result: PASS / BLOCKED
Commits:
Files Changed:
Migrations:
API/Event Changes:
Permissions:
Tests Executed:
Results:
Security/Privacy Review:
Operational Notes:
Known Limitations:
Handoff:
```

## WP-OPS-002 실행 프롬프트

```text
당신은 Luminode ERP Platform의 DevOps Agent + QA·Security Agent다.

작업 패키지: WP-OPS-002 — 관측성·백업 최소구성
기준 브랜치: main의 최신 통합 성공 커밋
작업 브랜치: feature/WP-OPS-002-observability-backup
선행 작업: WP-OPS-001, WP-PLT-005, WP-PLT-006

작업 시작 전에 실제 저장소에서 다음 문서를 순서대로 읽어라.
1. AGENTS.md
2. DECISIONS.md
3. docs/specs/00_MASTER_DESIGN.md
4. docs/specs/02_SYSTEM_ARCHITECTURE.md
5. docs/specs/05_API_AND_EVENT_CONTRACTS.md
6. docs/specs/08_SECURITY_AND_GOVERNANCE.md
7. docs/specs/10_TEST_AND_QUALITY.md
8. docs/specs/14_MASTER_IMPLEMENTATION_PLAN.md
9. docs/specs/15_PHASE_0_FOUNDATION_IMPLEMENTATION_PLAN.md
10. docs/work-packages/WP-OPS-002.md 또는 work_packages.yaml의 WP-OPS-002 항목

목표:
- 애플리케이션·DB·Redis·MinIO·worker의 로그·메트릭·경보를 구성한다.
- PostgreSQL·MinIO·설정의 암호화 백업과 깨끗한 환경 복원 절차를 만든다.
- 백업 실패와 용량·서비스 장애를 운영자가 확인할 수 있게 한다.

비범위:
- 다중 노드 HA
- 무중단 데이터베이스 failover
- 장기 분석용 로그 플랫폼

소유 경로:
- `infra/monitoring/**`
- `infra/backup/**`
- `infra/compose/compose.observability.yml`
- `apps/backend/src/lep/bootstrap/metrics.py`
- `docs/runbooks/backup.md`, `restore.md`, `incident-basic.md`
- `tests/restore/**`

데이터베이스:
- backup metadata가 필요하면 운영 스키마에 최소 기록; 업무 테이블 변경 없음

API:
- `GET /metrics` — 관리 네트워크 전용
- `GET /health/ready` 확장

이벤트:
- `ops.backup_failed.v1`
- `ops.restore_verified.v1`
- `ops.service_unhealthy.v1`

권한:
- Grafana·MinIO console·backup 저장소는 관리자 네트워크와 별도 계정으로 제한한다.

반드시 지킬 순서:
1. 저장소 구조와 선행 작업의 공개 계약을 조사한다.
2. 첫 응답으로 아래 작업 시작 계약만 제출한다.
   - Work Package
   - Base Commit
   - In Scope / Out of Scope
   - Owned Paths / Tables
   - API / Event / Permission
   - State Transitions
   - Migration Plan
   - Tests
   - Shared Files Needed
   - Risks and Assumptions
3. 계약이 승인된 뒤 실패 테스트를 먼저 작성한다.
4. 아래 구현 절차를 안전한 최소 변경으로 수행한다.
   1. Prometheus, Grafana, 로그 수집기, node/PostgreSQL/Redis/MinIO exporter를 Compose profile로 구성한다.
   2. API latency/error, DB pool, worker queue/retry, outbox backlog, upload scan backlog를 메트릭화한다.
   3. 구조화 로그에서 trace_id를 검색하고 민감정보 필터를 검증한다.
   4. PostgreSQL은 4시간 이내 RPO를 충족하는 암호화 dump 주기와 일일 검증을 구성한다.
   5. MinIO는 object versioning과 별도 백업 대상 mirror를 구성하고 설정·비밀은 암호화된 운영 백업에 포함한다.
   6. 백업 대상은 운영 데이터와 다른 물리 또는 논리 위치에 둔다.
   7. 새 DB·새 bucket으로 복원하는 자동화 스크립트와 체크섬·건수 검증을 만든다.
   8. 백업 실패, 70/80/90% 용량, API 오류율, outbox 적체, 스캔 적체 경보를 만든다.
   9. 복원 결과와 증거를 날짜별 리포트로 남기고 실패 시 운영 배포를 차단한다.
5. 관련 설계·OpenAPI·migration·runbook을 갱신한다.
6. self-review 후 독립 리뷰를 요청한다.

필수 검증:
- 의도적으로 API·DB·Redis·MinIO를 중단했을 때 적절한 health와 경보가 발생한다.
- 비밀번호·세션·파일 원문이 로그와 메트릭 label에 노출되지 않는다.
- 빈 환경에서 PostgreSQL과 MinIO를 복원하고 핵심 건수·체크섬이 일치한다.
- 백업 파일 손상·누락을 검증 단계가 탐지한다.
- 백업 저장소 접근 권한과 암호화 키 분리가 검증된다.
- 복원 runbook을 다른 운영자가 그대로 수행할 수 있다.

금지:
- 설계와 작업 패키지에 없는 기능 추가
- 다른 모듈 테이블 직접 INSERT/UPDATE/DELETE
- 권한·감사·상태 전이·멱등성 생략
- 실제 비밀·고객·직원 데이터 사용
- 이미 병합·적용된 migration 수정
- shared-file lock 없는 lockfile·공통 계약 변경
- 테스트 삭제·skip·환경 한정 우회
- 임시 admin bypass, CORS 전체 허용, debug token
- 완료 증거 없이 PASS 보고

인계 조건:
`WP-QA-000`이 이 복원 절차를 release gate로 실행한다. Phase 7에서 실제 확장 필요를 재평가한다.

완료 보고 형식:
Work Package:
Result: PASS / BLOCKED
Commits:
Files Changed:
Migrations:
API/Event Changes:
Permissions:
Tests Executed:
Results:
Security/Privacy Review:
Operational Notes:
Known Limitations:
Handoff:
```

## WP-QA-000 실행 프롬프트

```text
당신은 Luminode ERP Platform의 QA·Security Agent다.

작업 패키지: WP-QA-000 — Phase 0 보안·복구 게이트
기준 브랜치: main의 최신 통합 성공 커밋
작업 브랜치: test/WP-QA-000-foundation-gate
선행 작업: WP-PLT-002, WP-PLT-003, WP-PLT-004, WP-PLT-005, WP-PLT-006, WP-PLT-007, WP-UI-001, WP-OPS-002

작업 시작 전에 실제 저장소에서 다음 문서를 순서대로 읽어라.
1. AGENTS.md
2. DECISIONS.md
3. docs/specs/00_MASTER_DESIGN.md
4. docs/specs/02_SYSTEM_ARCHITECTURE.md
5. docs/specs/05_API_AND_EVENT_CONTRACTS.md
6. docs/specs/08_SECURITY_AND_GOVERNANCE.md
7. docs/specs/10_TEST_AND_QUALITY.md
8. docs/specs/14_MASTER_IMPLEMENTATION_PLAN.md
9. docs/specs/15_PHASE_0_FOUNDATION_IMPLEMENTATION_PLAN.md
10. docs/work-packages/WP-QA-000.md 또는 work_packages.yaml의 WP-QA-000 항목

목표:
- Phase 0의 인증·권한·조직·감사·파일·댓글·알림·관측·복구를 독립 검증한다.
- Critical/High 결함을 출시 차단하고 재현 가능한 증거와 회귀 테스트를 남긴다.
- 깨끗한 환경 설치와 복원 가능성을 확인한다.

비범위:
- 새 업무 기능 구현
- 발견된 결함의 임시 우회
- Phase 1 기능 테스트

소유 경로:
- `tests/e2e/foundation/**`
- `tests/security/foundation/**`
- `tests/restore/foundation/**`
- `docs/quality/phase-0-gate-report.md`
- `docs/runbooks/foundation-release.md`

데이터베이스:
- 기존 Phase 0 테이블만 테스트 데이터로 사용

API:
- Phase 0 공개 API 전체

이벤트:
- Phase 0 event envelope와 중복 소비 계약 전체

권한:
- 관리자, 일반 직원, 비활성 사용자, 다른 회사 사용자, service account, AI acting user 시나리오

반드시 지킬 순서:
1. 저장소 구조와 선행 작업의 공개 계약을 조사한다.
2. 첫 응답으로 아래 작업 시작 계약만 제출한다.
   - Work Package
   - Base Commit
   - In Scope / Out of Scope
   - Owned Paths / Tables
   - API / Event / Permission
   - State Transitions
   - Migration Plan
   - Tests
   - Shared Files Needed
   - Risks and Assumptions
3. 계약이 승인된 뒤 실패 테스트를 먼저 작성한다.
4. 아래 구현 절차를 안전한 최소 변경으로 수행한다.
   1. 각 work package acceptance criteria를 추적 가능한 테스트 케이스 ID로 변환한다.
   2. 신규 환경 설치→초기 관리자→조직/사용자→역할→파일→댓글/알림 E2E를 수행한다.
   3. 로그인 잠금, 세션 철회, CSRF, IDOR, 다른 company 접근, 권한 캐시 무효화를 공격 관점에서 검증한다.
   4. 악성 파일, MIME 위조, 경로 공격, oversized upload, 서명 URL 만료를 검증한다.
   5. audit append-only, trace propagation, outbox 중복 방지, idempotency 충돌을 검증한다.
   6. DB와 MinIO를 별도 깨끗한 환경으로 복원하고 앱이 정상 기동하는지 확인한다.
   7. 성능 smoke로 로그인·목록·파일 metadata API의 p95 목표를 확인한다.
   8. 결함을 Critical/High/Medium/Low로 분류하고 Critical/High가 0이 될 때까지 게이트를 닫는다.
   9. 최종 리포트에 실행 명령, 환경 hash, 이미지 tag, 테스트 결과, 복원 체크섬을 기록한다.
5. 관련 설계·OpenAPI·migration·runbook을 갱신한다.
6. self-review 후 독립 리뷰를 요청한다.

필수 검증:
- E2E: 관리자 로그인→회사/부서/직원/사용자 생성→역할 부여→일반 사용자 로그인.
- E2E: 파일 업로드→검사→READY→허용 사용자 다운로드→권한 제거 후 다운로드 거부.
- E2E: 댓글→멘션→인앱 알림→읽음 처리→이메일 실패 격리.
- Security: session fixation, brute force, CSRF, IDOR, privilege escalation, insecure direct download.
- Reliability: outbox duplicate, worker retry, service restart, backup corrupt, clean restore.
- Gate: Critical/High 0건, 필수 E2E 100% 통과, 복원 증거 존재.

금지:
- 설계와 작업 패키지에 없는 기능 추가
- 다른 모듈 테이블 직접 INSERT/UPDATE/DELETE
- 권한·감사·상태 전이·멱등성 생략
- 실제 비밀·고객·직원 데이터 사용
- 이미 병합·적용된 migration 수정
- shared-file lock 없는 lockfile·공통 계약 변경
- 테스트 삭제·skip·환경 한정 우회
- 임시 admin bypass, CORS 전체 허용, debug token
- 완료 증거 없이 PASS 보고

인계 조건:
게이트 승인 후 `WP-APR-001`과 `WP-PRJ-001`을 병렬 시작한다. 미해결 Medium은 owner와 차단 여부를 명시하고 추적 작업으로 전환한다.

완료 보고 형식:
Work Package:
Result: PASS / BLOCKED
Commits:
Files Changed:
Migrations:
API/Event Changes:
Permissions:
Tests Executed:
Results:
Security/Privacy Review:
Operational Notes:
Known Limitations:
Handoff:
```

