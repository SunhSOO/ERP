# WP-MAIL-LOADING-PERFORMANCE

Work Package ID: WP-MAIL-LOADING-PERFORMANCE
Owned Module: mail adapter + mail listing path
Goal: 반복 POP3 수집을 줄이고 메일 목록이 건수·상세·프로젝트 조회를 기다리지 않도록 개선
In Scope: `HiworksMailAdapter`의 `list_recent` 캐시/동시 수집 공유, TTL, 설정 변경 무효화, 오버레이 재적용 및 응답 사본 분리; 메일 화면 독립 로딩과 회귀 테스트
Out of Scope: 외부 POP3 접속, production DB/배포, migration, 기존 승인 도메인 정책 변경
Dependencies: `apps/backend/src/lep/modules/mail/infrastructure/hiworks_pop3.py`, `apps/backend/src/lep/modules/mail/public.py`, `docs/work-packages/WP-MAIL-LOADING-AUDIT.md`
API/Event contracts used: `/api/v1/projects/{project_id}/mail`, `/api/v1/projects/{project_id}/mail/counts`, `/api/v1/mail/{message_id}` (`mail` 서비스에서 기존 contracts 유지)
Tables owned: none
Permissions affected: none (adapter 캐시만 적용, DB 필터/권한은 기존 경로 유지)
Migration needed: none
Tests required:
- `apps/backend/tests/test_mail_preview_cache.py`:
  - 반복 list 호출 1회 fetch 보장
  - 동시 list 중복 호출에서 단일 fetch 보장
  - TTL 만료 후 재조회
  - TTL 시작 시점이 fetch 완료 기준인지 검증
  - 실패 후 retry
  - refresh 실패 시 만료된 캐시가 반환되지 않음
  - 빈 목록 캐시
  - adapter 설정(identity) 변경 강제 refresh
  - in-flight 동안 identity 변경 시 새 계정 스냅샷이 반영되는 회귀
  - 응답 뮤테이션이 캐시 원본/첨부까지 오염시키지 않음
  - overlay 갱신 반영
  - full detail(`get_message`)은 캐시 회피
- 기존 회귀: `apps/backend/tests/test_mail_approval.py`, `apps/backend/tests/test_mail_drive_links.py`

Results (2026-09-09):
- `apps/backend/tests/test_mail_preview_cache.py`에 인플라이트 설정 변경 회귀, TTL 시작 시점, 실패 갱신 미사용, 인스턴스 분리 테스트를 추가했다.
- `_snapshot`는 `_cache_loading`/`_cache_error`/`Condition` 기반 동기화를 제거하고, 인스턴스 단일 `Lock` 기반으로 단일 플라이트와 identity 변경 중간 점검을 적용했다.
Risks/assumptions:
- 단일 프로세스 인스턴스 내에서만 snapshot 공유(인스턴스 간 공유 없음)
- TTL은 성공 완료 시점의 `time.monotonic()` 기준 30초
- 만료된 snapshot은 실패 시 재사용하지 않음(“no stale on failure”)
- 기존 cold fetch 속도 최적화 보장 없음; 최초 호출은 기존 비용 유지
- 비밀은 로깅/노출 없이 저장, 캐시 식별은 해시된 형태로만 다룸

Per-process cache behavior:
- `list_recent()`의 원본 preview 스냅샷을 인스턴스 내부 필드에 TTL(30초)로 보관한다.
- 동일 인스턴스 내 동일 config(host/port/user/password/limit/domains)에서는 중첩/연속 `list_recent` 호출이 `_fetch()`를 공유한다.
- TTL은 `_fetch()` 성공 완료 시점에만 갱신한다.
- 실패 시 스냅샷/시간은 갱신되지 않으며, 만료된 캐시를 서빙하지 않는다.

## 총괄 검증 및 남은 작업 (2026-09-09)

### Phase 1: Backend cache (완료)
- 작성 모델: GPT-5.3 Codex Spark. 원본 미리보기 캐시·동시 수집 공유·설정 변경 중 수집 결과 폐기 구현.
- 최종 실행: `.venv/Scripts/python.exe -m pytest apps/backend/tests/test_mail_preview_cache.py apps/backend/tests/test_real_adapters.py apps/backend/tests/test_mail_approval.py apps/backend/tests/test_mail_drive_links.py -q --basetemp=.mail-review-runs/cache-final-tests --tb=short` → 158 passed (19.87s).
- 소유 adapter/캐시 테스트 Ruff PASS, adapter mypy PASS, adapter diff whitespace check PASS.
- 동일 합성 진단 재실행: 목록 3회 + 상세 1회에서 TOP 900→300, 연결 4→2, RETR 1 유지. 목록 2페이지 + 건수 service probe에서 TOP 900→300, 연결 3→1. 실제 외부 서버 지연 시간을 측정한 결과는 아니다.
- API/Event/DB migration 변경 없음. 분류 상태·권한·감사는 기존 DB 처리로 유지, 전체 상세/첨부 다운로드는 캐시하지 않는다.
- 제한: 프로세스별 30초 캐시로 첫 수집은 여전히 필요하고 새 메일 노출에 최대30초 지연 가능. 운영 배포는 수행하지 않았다.

### Phase 2: Frontend deferred loading (✅ 완료)
- 작성 모델: Claude Haiku 4.5. 목록·건수·상세·프로젝트의 독립 로딩 구현 및 재검증.

- 최종 수정 (A/B/C):
  A) TypeScript: MailDetailSectionProps.projectsPromise → Promise<MailProjectsResult>, 미사용 import 제거
  B) 테스트 매칭: 리전 스코핑, 오류 메시지 정확도, approved/unclassified 분리, freshness 기간 문구
  C) 선택 경계: MailDetailSection key=[projectId,status,targetId,linked_file_id] 추가로 재선택 시 이전 상세 제거

- 테스트:
  - `MailPage.test.tsx`: 19 cases (원본 유지) + renderPage async act() 래퍼 추가
  - `MailPage.loading.test.tsx`: 15 cases 최종 (병렬 개시 1 + 독립 로딩 13 + 선택 경계 1)
    - async act, 스코프 있는 텍스트 매칭 (region/heading), try/finally cleanup
    - unknown 타입 사용 (Error 대신)
    - 건수/상세/프로젝트 지연 중 목록 렌더링
    - 병렬 개시 검증: 건수/프로젝트가 목록 전에 시작
    - 프로젝트 실패 회귀: 목록/상세는 표시, 폼/네비만 오류
    - linked_file_id 미일치: 원본 소스 메시지 유지
    - nonadmin 검증: 건수 헤더/로딩 없음, 30초 안내만 표시

- 구현 최종:
  - Page: 목록 전에 counts/projects 시작 (rejection handler 포함), 각 독립 컴포넌트에서 결과 소비
  - MailProjectsResult union: {ok:true,projects:[]} | {ok:false}
  - Components: React19 use() + Suspense, 독립 오류 표시
    - MailCountsHeader: admin만 마운트
    - MailTabCountBadge: 각 탭별
    - MailProjectsNav: 프로젝트 실패 시 "프로젝트를 불러올 수 없습니다"
    - MailDetailSection: linked_file_mismatch 메시지 ("원본 소스를 사용할 수 없습니다…")
    - MailApprovalFormDeferred: 프로젝트 실패 시 "승인 프로젝트를 불러올 수 없습니다"
  - createDetailResult: linked_file_id 체크 시 error:"linked_file_mismatch"
  - 기존 보안/폼/네비게이션 유지, 30초 freshness note 추가

- 최종 수정 (iterative 완료):
  - MailDetailSection: can_review=false일 때 approval form 미렌더
  - 테스트 선택 경계: startTransition() + rerender() + waitFor로 React 트랜지션 시뮬레이션, key 변경으로 old detail 제거 검증
  - 텍스트 매칭: 정확도(period), 영역 스코핑(region/list), 다중 요소 처리 개선

- 최종 결과: ✅ 34/34 tests PASS, typecheck PASS, lint PASS
  - 19 original MailPage tests preserved
  - 15 new loading/boundary tests (1 parallel + 13 deferred + 1 selection boundary w/ transition)

## 총괄 최종 검증 (2026-09-09)

- Completed Work Package: WP-MAIL-LOADING-PERFORMANCE (로컬 구현·검증 완료)
- Files/Modules changed: mail POP3 adapter/캐시 테스트, 메일 page, MailDetailSection/MailCountsHeader/MailTabCountBadges/MailProjectsNav/MailApprovalFormDeferred/mail-deferred-results, MailPage 테스트 및 본 인계 문서.
- Behavior delivered: 목록을 먼저 표시하고 건수·전체 상세·프로젝트 선택지는 독립 로딩/실패 처리. 프로젝트별 분류됨/미분류 등 분류 탐색과 20건 이전·다음 페이지 유지. 메일 선택 전환 시 이전 본문이 사라지고 새 상세 로딩 표시를 검증.
- API/Event contracts: 변경 없음. Migrations: 없음. Permissions/Audit: 기존 서버 검사·승인·감사 경로 유지.
- Tests run and results: `corepack pnpm --filter @lep/web exec vitest run src/widgets/mail --reporter=dot` → 10 files, 118 passed. `corepack pnpm --filter @lep/web typecheck`, `lint`, `build` 모두 exit 0. 빌드는 메일 동적 경로 생성까지 성공. Backend 158 passed 및 Ruff/mypy 검증은 Phase 1 기록 참조.
- Known limitations: 실제 운영 메일함의 응답 시간·브라우저 검증은 수행하지 않음. 최초 POP3 수집 비용은 남아 있음. 30초 캐시는 요청 시 갱신하며 자동 새로고침을 추가한 것은 아님. 운영 배포하지 않음.
- Follow-up dependencies: 배포 후 실제 메일함에서 초기/재방문 응답 시간 및 화면 확인 필요.

## GAILAB 메일 품질 릴리스 (2026-09-09)

- 사용자 표기는 GAILAB으로 변경했다. 내부 `LEP_*` 계약, Docker 이미지·볼륨·서버 경로는 유지했다.
- 첨부 다운로드는 RFC 5987 `filename*`와 확장자를 보존하는 ASCII fallback을 함께 전송한다.
- 목록 안에서 선택한 메일은 목록 결과를 신뢰해 열고, 외부 deep link는 기존 프로젝트·연결 파일 검사를 유지한다.
- 프로젝트 추천은 코드·명칭·고객사 및 해당 프로젝트의 승인 메일 맥락만 사용한다. 자동 분류·자동 승인은 하지 않으며, 관리자는 미분류 목록에서 추천 있음/없음으로 필터링하고 대상 프로젝트를 바꿔 승인할 수 있다.
- API 목록은 기존 페이지 단위 계약을 사용하며 추천 필터는 페이지 분할 전에 적용한다.
- 검증: backend `test_mail_approval.py`, `test_mail_preview_cache.py`, `test_mail_drive_links.py`, `test_mail_recommendations.py` **131 passed**; web 메일 위젯 및 layout 테스트 **126 passed**; typecheck, lint, production build 통과.
- 운영 `/opt/luminode/ERP`에 대상 파일 11개만 전송해 API·web을 재빌드했다. 이전 파일은 `.deploy-backups/gailab-mail-20260909-1550`에 보관했다. API·web 컨테이너 healthy, API `/health/ready`의 database/vault/uploads 모두 ok, 웹 `/`은 로그인 리다이렉트 307을 확인했다.
