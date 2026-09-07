# Luminode ERP Platform 마스터 구현 계획

- 문서 상태: 구현 전 사용자 검토
- 작성일: 2026-08-05
- 기준 설계: `LUMINODE_ERP_DETAILED_DESIGN.md`
- 기준선 승인: `APPROVAL_RECORD.md`
- 작업 단위: `work_packages.yaml`의 71개 패키지
- 상세 구현 범위: 전체 단계의 실행 순서 + Phase 0 원자 단위 계획

## 1. 목적

이 문서는 승인된 ERP 상세설계를 여러 개발 에이전트가 충돌 없이 구현하도록 바꾸는 실행 기준이다. 전체 기능을 한 번에 생성하는 방식이 아니라, **계약 고정 → 독립 작업 → 통합 검증 → 단계 게이트 → 제한된 실사용** 순으로 진행한다.

이 문서가 확정되기 전에는 제품 코드를 만들지 않는다. 확정 후 첫 구현 대상은 `WP-PLT-001`이며, Phase 0이 끝날 때까지 업무 모듈 기능을 앞당겨 넣지 않는다.

## 2. 구현 원칙

1. **단계 게이트 고정**: Phase N의 QA 게이트를 통과하기 전 Phase N+1 기능을 운영 브랜치에 병합하지 않는다.
2. **한 작업 패키지, 한 책임**: 작업 패키지 하나는 한 주 에이전트가 소유하고 한 MR 또는 작은 연속 MR로 끝낸다.
3. **계약 우선**: API·이벤트·권한·상태 머신·테이블 소유권을 먼저 고정한 뒤 구현한다.
4. **테스트 우선**: 도메인 규칙과 버그는 실패 테스트를 먼저 작성한다.
5. **모듈 경계 유지**: 다른 모듈 테이블에 직접 쓰지 않는다. 필요한 변경은 application interface 또는 outbox event로 요청한다.
6. **운영 가능한 최소 구성**: 현재 10명 이하, 최대 30명에 필요한 수준을 우선하며 과도한 분산 시스템을 도입하지 않는다.
7. **AI 안전성 우선**: AI는 Tool API만 사용하며 중요 실행은 사람 승인 전에는 반영하지 않는다.
8. **복구 가능성 우선**: 배포 성공보다 백업 복원과 감사 추적 가능 여부를 먼저 검증한다.
9. **공유 파일 단일 소유자**: 루트 lockfile, Alembic head, OpenAPI 산출물, 공통 UI 토큰은 지정된 통합 에이전트만 최종 병합한다.
10. **완료 증거 필수**: 테스트 명령, 결과, migration, 화면 증거, 운영 문서를 남기지 않은 작업은 완료로 보지 않는다.

## 3. 구현 기준안

| 항목 | 기준 |
|---|---|
| 저장소 | 단일 Git 모노레포 |
| 기본 CI | GitLab CI 기준, 로컬 명령은 CI 공급자와 무관하게 유지 |
| 백엔드 | FastAPI 기반 단일 Python 코드베이스, API/worker/scheduler 별도 entrypoint |
| 프론트엔드 | Next.js + TypeScript 반응형 웹/PWA |
| 트랜잭션 DB | PostgreSQL |
| 캐시·큐 | Redis |
| 파일 | MinIO |
| 검색 | OpenSearch, Phase 5부터 활성화 |
| 벡터 검색 | Qdrant, Phase 5부터 활성화 |
| 배포 | Docker Compose, 개발·스테이징·운영 manifest 분리 |
| 인증 | HttpOnly 보안 세션 쿠키, 서버측 세션 철회, TOTP MFA |
| API | `/api/v1`, RFC 7807 오류, 낙관적 잠금, 상태 전이 endpoint |
| 이벤트 | PostgreSQL outbox + 멱등 소비자 |
| 시간·통화 | 저장은 UTC, 표시 Asia/Seoul, 기본 통화 KRW |
| 식별자 | UUID |
| 삭제 | 핵심 업무 엔터티는 상태 전이·보관, 물리 삭제 제한 |
| 외부 접속 | VPN 우선, DB/Redis/MinIO 직접 공개 금지 |

GitLab은 기준안이다. 실제 저장소가 GitHub인 경우 MR을 PR로 바꾸되 브랜치·품질 게이트·작업 패키지 규칙은 동일하게 유지한다.

## 4. 목표 저장소 구조

```text
luminode-erp/
├── AGENTS.md
├── README.md
├── DECISIONS.md
├── pyproject.toml
├── package.json
├── pnpm-workspace.yaml
├── .editorconfig
├── .gitignore
├── .env.example
├── .gitlab-ci.yml
├── apps/
│   ├── backend/
│   │   ├── pyproject.toml
│   │   ├── alembic.ini
│   │   ├── migrations/
│   │   ├── src/lep/
│   │   │   ├── api/
│   │   │   ├── bootstrap/
│   │   │   ├── common/
│   │   │   ├── modules/
│   │   │   ├── workers/
│   │   │   └── scheduler/
│   │   └── tests/
│   └── web/
│       ├── app/
│       ├── src/
│       │   ├── features/
│       │   ├── entities/
│       │   ├── shared/
│       │   └── widgets/
│       └── tests/
├── packages/
│   ├── api-client/
│   ├── ui/
│   ├── eslint-config/
│   └── tsconfig/
├── infra/
│   ├── compose/
│   ├── edge/
│   ├── monitoring/
│   ├── backup/
│   └── scripts/
├── tests/
│   ├── contract/
│   ├── e2e/
│   ├── performance/
│   ├── restore/
│   └── security/
├── docs/
│   ├── specs/
│   ├── adr/
│   ├── api/
│   ├── runbooks/
│   └── work-packages/
└── scripts/
    ├── bootstrap.sh
    ├── bootstrap.ps1
    ├── check_boundaries.py
    ├── generate_client.sh
    └── verify.sh
```

### 4.1 백엔드 모듈 표준

```text
modules/<module>/
├── domain/
│   ├── entities.py
│   ├── value_objects.py
│   ├── policies.py
│   ├── events.py
│   └── errors.py
├── application/
│   ├── commands/
│   ├── queries/
│   ├── dto.py
│   └── ports.py
├── infrastructure/
│   ├── models.py
│   ├── repositories.py
│   └── adapters.py
├── api/
│   ├── router.py
│   ├── requests.py
│   └── responses.py
└── tests/
```

`domain`은 FastAPI, SQLAlchemy, Redis, MinIO를 import하지 않는다. `application`은 포트에만 의존하고, `infrastructure`가 포트를 구현한다. 다른 모듈이 필요한 경우 해당 모듈의 공개 application interface 또는 이벤트를 사용한다.

### 4.2 프론트엔드 표준

- `app/`: 라우팅과 페이지 조립
- `features/`: 로그인, 사용자 생성, 파일 업로드처럼 사용자 행동 단위
- `entities/`: 사용자, 부서, 알림 등 도메인 표시 모델
- `shared/`: API client, 권한 helper, 공통 상태, locale
- `widgets/`: 앱 셸, 목록 레이아웃, 활동 패널 등 복합 UI
- `packages/ui`: 버튼, 입력, 표, 다이얼로그, 상태 배지 등 도메인 비종속 컴포넌트

페이지가 직접 HTTP 요청을 만들지 않는다. OpenAPI로 생성한 `packages/api-client`를 사용하며 권한 숨김은 서버 권한 검사를 대체하지 않는다.

## 5. 공통 계약 고정 순서

각 모듈 작업은 다음 순서를 지킨다.

1. 유스케이스와 비범위를 작업 패키지에 기록한다.
2. permission code와 scope를 확정한다.
3. 상태 머신과 금지 전이를 테스트로 작성한다.
4. 소유 테이블과 unique/FK/check/index를 확정한다.
5. request/response/event schema를 작성한다.
6. application service를 구현한다.
7. adapter와 API를 구현한다.
8. audit/outbox/idempotency를 연결한다.
9. frontend와 generated client를 연결한다.
10. 단위·통합·권한·계약·E2E 테스트를 통과한다.
11. 운영·복구·사용자 문서를 갱신한다.
12. 독립 리뷰와 통합 에이전트 검증 후 병합한다.

## 6. 에이전트 운영 모델

### 6.1 역할

| 역할 | 책임 | 코드 소유 범위 |
|---|---|---|
| Coordinator Agent | 작업 패키지 상태·의존성·통합 브랜치 관리 | `docs/work-packages`, 실행 보드 |
| Architect Agent | 경계·계약·ADR·breaking change 검토 | `docs/adr`, 공개 계약 |
| Platform Backend Agent | 공통 백엔드·IAM·감사·outbox | `apps/backend/src/lep/bootstrap`, `common`, `modules/iam` |
| Domain Agent | 지정 업무 모듈 | 해당 `modules/<domain>` |
| Frontend/UX Agent | 앱 셸·화면·공통 UI | `apps/web`, `packages/ui`의 승인된 범위 |
| DevOps Agent | Compose·CI·관측·백업 | `infra`, 배포 스크립트 |
| Data/Migration Agent | Alembic·이관·검증 | 지정 migration과 import 도구 |
| AI/Search Agent | 검색·RAG·AI 도구 | `modules/search`, `modules/ai`, 관련 worker |
| QA·Security Agent | 수용 기준·권한·보안·복구 게이트 | `tests`, 리뷰 리포트 |
| Integration Agent | 공유 파일·생성 산출물·최종 merge | lockfile, Alembic head, generated client |

### 6.2 병렬성 제한

- 구현 에이전트는 한 파동에서 최대 3개를 기본으로 한다.
- 리뷰 에이전트는 구현 에이전트와 분리한다.
- 같은 모듈, 같은 migration chain, 같은 공통 UI 패키지를 두 에이전트가 동시에 수정하지 않는다.
- `pyproject.toml`, `pnpm-lock.yaml`, 공통 OpenAPI, Alembic merge revision은 Integration Agent가 최종 반영한다.
- 다음 파동은 선행 작업이 기본 브랜치에 병합되고 CI가 통과한 뒤 시작한다.

### 6.3 Git worktree 기준

각 에이전트는 별도 worktree와 브랜치를 사용한다.

```bash
git worktree add ../lep-WP-PLT-001 -b feature/WP-PLT-001-repository-bootstrap
git worktree add ../lep-WP-OPS-001 -b feature/WP-OPS-001-compose-foundation
```

한 에이전트가 다른 에이전트 worktree를 수정하지 않는다. 공유 계약 변경은 먼저 Architect Agent의 승인 기록을 남긴다.

## 7. 작업 패키지 생명주기

```text
PROPOSED
  → READY
  → CONTRACT_REVIEW
  → IN_PROGRESS
  → SELF_TESTED
  → DOMAIN_REVIEW
  → QA_SECURITY_REVIEW
  → INTEGRATION
  → DONE
```

### READY 조건

- 모든 dependency가 `DONE`
- 작업 범위와 비범위가 작성됨
- 소유 파일·테이블·API가 겹치지 않음
- acceptance criteria가 테스트 가능함
- 미확정 결정이 없음

### DONE 조건

- 수용 기준 전부 통과
- migration과 rollback/forward-fix 문서 존재
- API·이벤트·권한 문서 갱신
- 감사와 민감정보 로그 검증
- 단위·통합·권한 테스트 통과
- 관련 E2E 또는 회귀 테스트 통과
- 사용자 화면의 loading/empty/error/forbidden/conflict 상태 구현
- MR 리뷰 지적사항 해결
- 기본 브랜치 병합 후 통합 CI 통과

## 8. 단계별 실행 파동

### Phase 0 — 기반 플랫폼

| 실행 파동 | 작업 패키지 |
|---|---|
| 0.1 | `WP-PLT-001` 저장소·모듈 경계 부트스트랩 |
| 0.2 | `WP-OPS-001` Docker Compose 개발·스테이징 기반 |
| 0.3 | `WP-PLT-002` 인증·세션·MFA 기반 |
| 0.4 | `WP-PLT-003` 회사·부서·직원·사용자 관리<br>`WP-UI-001` 디자인 시스템·전역 레이아웃 |
| 0.5 | `WP-PLT-004` RBAC·범위 권한 엔진 |
| 0.6 | `WP-PLT-005` 감사 로그·활동 로그·Outbox |
| 0.7 | `WP-PLT-006` 파일 업로드·검사·MinIO 기반<br>`WP-PLT-007` 댓글·멘션·알림 기반 |
| 0.8 | `WP-OPS-002` 관측성·백업 최소구성 |
| 0.9 | `WP-QA-000` Phase 0 보안·복구 게이트 |

**종료 게이트:** 인증·권한·감사·파일·알림·백업·복구가 통합 검증되고 Critical/High 결함이 없다.

### Phase 1 — 프로젝트 운영 코어

| 실행 파동 | 작업 패키지 |
|---|---|
| 1.1 | `WP-APR-001` 일반 전자결재<br>`WP-PRJ-001` 프로젝트·멤버·상태 |
| 1.2 | `WP-CAL-001` 캘린더·회의·회의록 수동 기능<br>`WP-DMS-001` 문서·폴더·불변 버전<br>`WP-PRJ-002` 프로젝트 템플릿·마일스톤<br>`WP-PRJ-003` 업무·하위업무·의존성<br>`WP-PRJ-004` 리스크·이슈·의사결정 |
| 1.3 | `WP-DMS-002` 산출물·검토·제출 |
| 1.4 | `WP-UI-PRJ-001` 프로젝트 통합 홈·받은 작업함 |
| 1.5 | `WP-QA-P1` Phase 1 프로젝트 파일럿 게이트 |

**종료 게이트:** 프로젝트 파일럿 사용자가 프로젝트·업무·회의·문서·산출물·일반결재를 한 흐름으로 수행한다.

### Phase 2 — CRM·영업·견적·계약

| 실행 파동 | 작업 패키지 |
|---|---|
| 2.1 | `WP-CRM-001` 고객사·담당자 |
| 2.2 | `WP-CRM-002` 리드·영업활동<br>`WP-SAL-001` 영업기회·파이프라인 |
| 2.3 | `WP-SAL-002` 품목 카탈로그·견적 버전 |
| 2.4 | `WP-CON-001` 계약·버전·보안등급 |
| 2.5 | `WP-AUT-001` 수주·계약→프로젝트 전환<br>`WP-CON-002` 계약 의무·지급 일정·갱신 |
| 2.6 | `WP-UI-COM-001` 영업·계약 통합 UX |
| 2.7 | `WP-QA-P2` Phase 2 수주 여정 게이트 |

**종료 게이트:** 고객 등록부터 수주·계약·프로젝트 전환까지 E2E가 통과하고 계약 원본과 버전 이력이 보존된다.

### Phase 3 — 결재·구매·재무·자산

| 실행 파동 | 작업 패키지 |
|---|---|
| 3.1 | `WP-APR-002` 조건부 결재·대결·SLA |
| 3.2 | `WP-FIN-001` 비용·증빙·예산<br>`WP-PUR-001` 공급사·구매요청·견적비교 |
| 3.3 | `WP-PUR-002` 발주·부분입고·검수·반품 |
| 3.4 | `WP-AST-001` 자산·대여·점검·폐기<br>`WP-FIN-002` 매출·수금·매입·지급 상태<br>`WP-INV-001` 소모품 재고 원장 |
| 3.5 | `WP-AUT-002` 입고→자산/재고 반영<br>`WP-FIN-003` 프로젝트 손익·스냅샷<br>`WP-INT-ACC-001` 외부 회계 내보내기 |
| 3.6 | `WP-QA-P3` Phase 3 운영·재무 게이트 |

**종료 게이트:** 구매요청부터 입고·자산/재고 반영, 비용·손익 집계까지 수치 검증이 통과한다.

### Phase 4 — 인사·근태·휴가

| 실행 파동 | 작업 패키지 |
|---|---|
| 4.1 | `WP-HR-001` 인사 프로필·기술·자격 |
| 4.2 | `WP-AUT-003` 퇴사·인계·회수 워크플로우<br>`WP-HR-002` 근태·수정 신청<br>`WP-HR-003` 휴가 부여·잔여·신청<br>`WP-HR-004` 교육·평가 기초 |
| 4.3 | `WP-QA-P4` Phase 4 인사 개인정보 게이트 |

**종료 게이트:** 직원·근태·휴가·퇴사 인계 흐름이 개인정보 권한과 감사 기준을 충족한다.

### Phase 5 — 검색·지식·AI 읽기 기능

| 실행 파동 | 작업 패키지 |
|---|---|
| 5.1 | `WP-SRCH-001` 통합 키워드 검색·색인 |
| 5.2 | `WP-KMS-001` 위키·지식 수명주기 |
| 5.3 | `WP-RAG-001` 문서 추출·청크·임베딩 파이프라인 |
| 5.4 | `WP-RAG-002` 권한 기반 하이브리드 검색 |
| 5.5 | `WP-AI-001` AI Gateway·대화·모델 정책 |
| 5.6 | `WP-AI-002` 프로젝트·문서·보고서 요약<br>`WP-AI-003` 회의 액션아이템 제안<br>`WP-AI-004` 산출물 누락·버전 점검 |
| 5.7 | `WP-AI-QA-001` RAG·AI 읽기 보안 게이트 |

**종료 게이트:** 검색/RAG가 원본 권한을 이중 검증하고 근거 링크를 제공하며 권한 누출 테스트를 통과한다.

### Phase 6 — 승인형 AI 업무 실행

| 실행 파동 | 작업 패키지 |
|---|---|
| 6.1 | `WP-AIT-001` Tool Registry·스키마·정책 엔진 |
| 6.2 | `WP-AIO-001` AI 관측성·비용·킬스위치<br>`WP-AIT-002` AI 승인 요청·고정 payload·재개 |
| 6.3 | `WP-AIA-001` 업무·리스크·검토요청 쓰기 도구 |
| 6.4 | `WP-AIA-002` 교차 모듈 승인형 자동화 |
| 6.5 | `WP-AI-QA-002` AI 도구 안전 게이트 |

**종료 게이트:** AI 도구가 위험등급·미리보기·승인·멱등성·킬스위치를 준수하고 안전 게이트를 통과한다.

### Phase 7 — 외부 연동·분석·인프라 고도화

| 실행 파동 | 작업 패키지 |
|---|---|
| 7.1 | `WP-ANL-001` 표준 KPI·리포트<br>`WP-INF-001` 서버·서비스·GPU 상태 연동<br>`WP-INT-CAL-001` 외부 캘린더 동기화<br>`WP-INT-GIT-001` GitHub/GitLab 메타데이터 연동<br>`WP-INT-MAIL-001` 이메일 발송·활동 연결 |
| 7.2 | `WP-ANL-002` 정기 보고서 생성·배포<br>`WP-INF-002` 장애·포스트모템<br>`WP-OPS-HA-001` 확장·고가용성 재평가 |
| 7.3 | `WP-QA-FINAL` 전사 릴리스·재해복구 게이트 |

**종료 게이트:** 필수 외부 연동·KPI·서버 상태·재해복구가 전사 릴리스 게이트를 통과한다.


## 9. 단계별 운영 전환

### Phase 0

내부 개발자와 관리자 계정만 사용한다. 기능 시연보다 인증·권한·파일·감사·복구 증거를 우선한다.

### Phase 1

한 개의 실제 프로젝트를 파일럿으로 선택한다. 기존 자료를 모두 이관하지 않고 진행 중인 업무·회의·산출물부터 입력한다. 파일럿 종료 후 사용자가 불편했던 입력 항목과 누락된 권한을 수정한다.

### Phase 2~4

영업·계약, 운영·재무, 인사를 각각 기존 장부와 병행 운영한다. 수치와 승인 결과를 대조한 뒤 해당 업무의 기준 시스템을 ERP로 전환한다. 법정 회계·급여 원장은 계속 외부 시스템을 기준으로 한다.

### Phase 5~6

AI는 읽기 전용 검색부터 시작한다. 답변 품질과 권한 누출 검증 후 초안, 승인형 실행 순으로 기능을 연다. 위험 등급 R4 이상은 운영 초기에도 자동 승인하지 않는다.

### Phase 7

외부 연동과 전사 리포트를 활성화한다. 연동 장애가 핵심 ERP 기능을 막지 않는지 확인하고 최종 재해복구 훈련 후 전체 운영 기준선을 확정한다.

## 10. CI/CD 품질 게이트

### 모든 MR

- 포맷, lint, type check
- secret scan, dependency scan
- 모듈 경계 검사
- backend unit/integration test
- frontend unit/component test
- OpenAPI breaking change 검사
- Alembic single-head 검사
- 컨테이너 build
- 변경된 permission matrix 테스트

### 단계 게이트

- 핵심 E2E
- IDOR·세션·CSRF·파일·인젝션 보안 테스트
- 성능 smoke
- 백업 복원
- 감사 로그 확인
- 운영 runbook 검증
- Critical/High 결함 0건

### 운영 배포

1. 태그된 불변 이미지를 생성한다.
2. 스테이징에서 migration과 smoke test를 수행한다.
3. DB 백업과 복원 가능성을 확인한다.
4. 운영 maintenance 필요 여부를 결정한다.
5. migration을 실행한다.
6. 애플리케이션을 배포한다.
7. health·로그·핵심 사용자 여정을 확인한다.
8. 실패 시 forward-fix 또는 승인된 rollback을 수행한다.

## 11. 데이터 이관 전략

1. **기준정보**: 회사, 부서, 직원, 역할, 프로젝트 코드 체계를 먼저 이관한다.
2. **진행 중 프로젝트**: 활성 프로젝트, 미완료 업무, 최신 산출물부터 이관한다.
3. **영업·계약·재무**: 현재 유효한 고객·계약·미수/미지급·자산을 우선한다.
4. **과거 문서**: 원본 보존, 체크섬, 문서 유형, 프로젝트 연결을 검증한 뒤 단계적으로 수집한다.
5. **AI 색인**: 원본 권한과 보존 정책이 확정된 문서만 수집한다.

모든 이관은 재실행 가능해야 하며 원본 건수, 대상 건수, 제외 사유, FK 오류, 금액 합계, 파일 체크섬을 리포트한다.

## 12. 관측성과 운영 기준

- 모든 요청과 비동기 작업에 `trace_id`
- 로그인 실패, 권한 거부, 상태 전이 실패, 파일 검사 실패, outbox retry를 메트릭화
- 구조화 로그에 비밀번호·토큰·문서 원문·주민번호 등 민감정보 금지
- DB, MinIO, 로그, 검색, 벡터 저장소 용량을 별도 경보
- 백업 성공만 보지 않고 정기 복원 결과를 기록
- 외부 연동은 retry와 dead-letter queue를 제공
- AI는 run/tool/approval/model/prompt version을 기록하고 kill switch를 제공

## 13. 주요 위험과 통제

| 위험 | 통제 |
|---|---|
| 에이전트가 설계 밖 기능을 추가 | 작업 패키지 비범위, Architect 리뷰, MR 범위 검사 |
| migration 충돌 | 파동별 migration 슬롯, Integration Agent가 head 병합 |
| 권한 누락·IDOR | object-level 권한 템플릿과 거부 테스트 필수 |
| 공통 파일 충돌 | 공유 파일 단일 소유, generated 산출물 통합 단계에서 갱신 |
| AI가 과도한 실행 | Tool Gateway, 위험 등급, payload 고정, 사람 승인 |
| 파일 악성코드·경로 공격 | 격리 업로드, 검사 완료 전 비공개, 체크섬, ZIP 방어 |
| 자체 서버 단일 장애 | 별도 백업, 복원 훈련, 데이터 볼륨 분리 |
| 검색 인덱스 권한 지연 | 인덱스 필터 + 원본 API 재검증 |
| 작은 조직의 과도한 입력 부담 | 프로젝트 중심 기본값, 템플릿, 필수 필드 최소화 |
| 단계가 길어져 실사용이 늦어짐 | Phase 1 파일럿을 최초 업무 가치 지점으로 고정 |

## 14. 구현 착수 순서

구현 계획 승인 후 다음 순서로 시작한다.

1. `WP-PLT-001` 전용 worktree를 만든다.
2. 루트 `AGENTS.md`, 설계 기준선, 모듈 경계 문서를 저장소에 반영한다.
3. backend/web 최소 실행 경로와 공통 검증 명령을 만든다.
4. Architect Agent와 QA Agent가 경계·재현성·비밀정보 검사를 승인한다.
5. 기본 브랜치 병합 후 `WP-OPS-001`을 시작한다.

상세한 파일별 절차는 `15_PHASE_0_FOUNDATION_IMPLEMENTATION_PLAN.md`를 따른다.
