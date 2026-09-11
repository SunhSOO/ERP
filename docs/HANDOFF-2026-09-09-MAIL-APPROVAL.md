# Handoff — 메일·첨부 승인 분류 (2026-09-09)

## 최신 추가 릴리스 — GAILAB 메일 품질 (2026-09-09)

이 절이 아래 이전 배포 이력보다 우선한다. 코드 작성은 사용자 지정 **Claude Haiku 4.5**로 진행했다.

- GAILAB 표기, 한글 첨부 파일명·확장자 보존 다운로드, 목록 내 상세 열기, 결정형 프로젝트 추천을 반영했다.
- 추천은 프로젝트 코드·명칭·고객사와 프로젝트별 승인 맥락만 근거로 한다. 추천은 사람이 변경 가능한 승인 기본값일 뿐 자동 분류·승인을 수행하지 않는다.
- 관리자 미분류 화면에 전체/추천 있음/추천 없음 필터를 추가했고, 필터는 목록 선택과 이전/다음 페이지에서 유지된다.
- 로컬 검증: 관련 backend **131 passed**, web **126 passed**, typecheck·lint·production build 통과.
- 운영 서버 `/opt/luminode/ERP`에는 대상 파일 11개만 배포했다. 배포 전 원본은 `.deploy-backups/gailab-mail-20260909-1550`에 보관했다. API·web·DB healthy, API 준비 검사 database/vault/uploads ok, 웹 루트 307(로그인 이동)을 확인했다.

## 최신 상태 — 재개 후 배포 완료 (2026-09-09)

이 절이 아래 중단 당시 기록보다 우선한다. 사용자 재개 및 모델 변경 지시에 따라 코드 작성은 **gpt-5.6-luna / low**로 진행했다. Claude 로그인이나 추가 호출은 하지 않았다.

- 운영 `/opt/luminode/ERP`에 메일 관련 48개 파일만 반영했다. 원본 HEAD는 `8313e3e`이고 배포 변경은 미커밋이다. 로컬의 별도 AI runtime/WBS/converter 변경은 보존했으며 이번 배포에서 제외했다. 공용 domain.ts는 메일/드라이브 타입 확장만 포함했다.
- 새 메일은 미분류이며 관리자 승인 후 프로젝트가 확정된다. 첨부는 사용자가 선택해 승인한 파일만 프로젝트 드라이브에 연결된다. 메일 승인 후 첨부 추가 승인도 가능하다. 미분류/프로젝트 분류/제외/전체 구분과 건수를 제공한다.
- `/`, `?`, `#` 등 UIDL 경로 문자는 opt-in `id_encoding=base64url`로 전달한다. DB와 응답 ID는 원래 UIDL이다. 잘못된 인코딩/제어문자/초과 길이는 422이며 프록시도 알 수 없는 인코딩을 거부한다.
- 신규 테이블 6개 생성 완료. 기존 테이블/업무 데이터 변경이나 실제 메일 승인·첨부 분류는 실행하지 않았다. API·웹만 재생성했고 DB·Ollama 컨테이너는 유지했다.
- 배포 후 `/health/live` 200, `/health/ready` 200, 웹 `/login` 200, 미인증 메일 단건 401, 승인/추가승인/제외 OpenAPI 및 인코딩 query 계약 PASS. API·웹·DB healthy.

### 실행한 검증

- 메일만 분리한 후보 backend 전체: **211 passed**. 이후 테스트만 추가·정정하여 같은 후보의 UIDL 회귀 **9 passed, 52 deselected**. 이 두 수치를 합산하지 않는다.
- 후보 웹 전체: **116 passed / 12 files**. 기존 URL 기대값 4건을 새 계약에 맞춘 뒤 최종 통과했다. 로컬 별도 AI 테스트는 분리 후보에 포함하지 않았다.
- API 및 웹 Docker build PASS. 최종 제품 소스와 빌드 이미지의 파일 일치 확인 PASS. 타입 검사, 소유 backend Ruff 및 API routes mypy PASS.
- 격리 PostgreSQL에서 합성 데이터로 저장/재조회/idempotency/충돌/추가첨부/outer rollback/savepoint rollback PASS. 기존 schema 대상 migration dry-run/apply/reapply PASS. QA DB는 자동 제거했다.

### 복구 및 운영 인계

- 복구본: 서버 `/home/administrator/lep-releases/mail-20260909/`.
- 이전 이미지: `luminode/api:before-mail-20260909`, `luminode/web:before-mail-20260909`.
- 복구본의 `original-files.tgz`, `new-files.txt`, `release-files.txt`, 이전 이미지 ID 파일 및 최종 `mail-code.tgz`를 보존했다. 비밀 파일은 포함하지 않았다.
- 긴급 runtime 복구: 위 이전 이미지를 각각 `luminode/api:local`, `luminode/web:local`로 tag한 뒤 `infra`에서 `docker compose up -d --no-deps api web`. 소스 복구는 original-files를 복원하고 new-files에 기록된 이번 신규 파일만 경로 검증 후 제거한다. 신규 감사/승인 테이블은 삭제하지 않는다.
- **제한:** 첨부 연결은 원본 메일 참조다. 영구 파일 복사/보관이 아니며 원본 삭제·변경 시 다운로드가 실패할 수 있다. 실제 사용자 로그인 후 메일 선택·승인 UI의 운영 업무 검증은 사용자가 수행해야 한다. 운영 계정 생성/인증 우회/업무 메일 승인으로 검증하지 않았다.
- 지식화 파일쓰기와 DB의 분산 원자성, 프로젝트 ACL 확장은 별도 후속 범위다. 이번 범위를 확대하지 않았다.

---

아래는 **이전 중단 시점의 이력**이다. 미배포·Claude 재개·미검증 표기는 위 최신 결과로 대체된다.

## 중단 지시
사용자가 이번 작업을 정리하고 handoff를 만든 뒤 토큰 절감을 위해 잠시 멈추라고 요청했다. 새 Claude 호출·범위 확장·자동 후속 작업을 하지 않는다. 재개는 사용자의 명시적 요청을 기다린다.

## 운영 상태
- 서버 `/opt/luminode/ERP`, HEAD `8313e3e`, working tree clean. 로컬 HEAD `e6dcfbd`와 원본 tree 내용 동일.
- 이번 작업은 **아직 서버에 배포하지 않았다. 운영 migration·승인·첨부 연결도 실행하지 않았다.** 서버에는 기존 동작이 남아 있다.
- API readiness와 웹 login HTTP200, 기존 컨테이너 healthy 확인. Hiworks 동시 읽기 연결2개에서 STAT만 성공 확인. 실제 메일 본문/첨부 조회·발송·삭제·분류 없음.
- SSH 세션 종료. 접속 비밀번호는 문서/코드/로그에 저장하지 않는다.
- 실행중이던 코드 작성 세션만 마무리한 뒤 코드 동결 및 필수 검사 결과를 아래에 기록한다.

## 구현한 범위와 계약
- 새 메일은 미분류. 발신 도메인 결과는 `suggested_project_id` 추천일 뿐 `project_id`를 확정하지 않는다.
- active admin이 프로젝트와 첨부를 선택해 승인. 기본 첨부 선택 없음. 메일만 먼저 승인하고 미연결 첨부를 나중에 추가 승인 가능.
- 미분류/분류완료/제외/전체 탭, URL 필터 및 pagination.
- 승인 상태·원문 snapshot·감사·idempotency를 DB에 저장. 버전 충돌·중복 요청·부분 저장을 방어.
- 승인된 첨부는 프로젝트 드라이브에 **메일 원본 참조**로 연결. 영구복사/보관/악성코드검사 완료를 의미하지 않는다. 원본 삭제·변경·메일함 교체 시 다운로드가 불가능할 수 있다.
- 승인 메일/연결 첨부 조회는 active admin 또는 대상 프로젝트 생성자. 승인 전 지식화는 서버에서 거부.
- 원본은 mailbox_key(호스트/계정 hash, 비밀번호 제외)+raw UIDL로 식별. Drive 다운로드의 linked_file_id query로 계정교체 시 다른 파일을 잘못 내려받지 않도록 검사.
- 신규 테이블6개: mail_reviews, mail_review_attachments, mail_idempotency_keys, mail_idempotency_links, mail_audit_log, document_mail_attachment_links. 기존 테이블 수정 없음.
- API: mail approve, attachments/approve, dismiss는 expected_version 및 Idempotency-Key 사용. 기존 단건/첨부/지식화 API에 승인 범위 검사. counts data는 객체, 목록 meta는 total/has_more/next_cursor.

## 파일 소유권
- Backend: `apps/backend/src/lep/modules/mail/**`, `common/schema.py`, `projects/api/routes.py`의 count 연결, `scripts/migrate_mail_review.py`, `tests/test_mail_approval.py`, `tests/test_real_adapters.py`의 메일 기대값.
- Documents: `modules/documents/{public.py,application/services.py,api/routes.py,domain/entities.py}`, 신규 `infrastructure/mail_link_models.py`, `mail_links.py`, `tests/test_mail_drive_links.py`.
- UI: 프로젝트 mail/drive page, `src/shared/data/mail-review*.ts`, `src/widgets/mail/**`, 기존 attachment proxy, `packages/api-client/src/domain.ts`의 mail/drive 필드.
- 설계: DECISIONS.md ADR-021 Approved 및 `docs/work-packages/2026-09-09-mail-approval.md`.

## 현재 변경과 섞인 이전 작업 — 보존할 것
같은 checkout에 이전 AI runtime·WBS domain·kordoc artifact 변경과 기존 메일 첨부 변경이 함께 있다. 커밋하지 않은 사용자 작업을 되돌리지 않는다.
- 이전 별도 작업: delivery/domain/transitions.py, document ports.py/kordoc_converter.py, integrations runtime 및 AI page/tests.
- 이번 메일 기능은 이전 converter artifact 포트/AI/WBS 기능 없이 독립적으로 배포할 수 있다.
- 통합검증 없이 working tree 전체를 서버로 복사하지 않는다. release 대상 파일 목록을 명시적으로 만든다.

## 검증 및 알려진 제한
- Documents 독립 최종: 37 pytest passed, Ruff/소유파일 mypy passed. SQLite outer rollback 실패를 재현 후 수정함.
- PostgreSQL smoke 스크립트: `.task-runs/2026-09-09/mail-postgres-smoke.py`. 문법/Ruff 및 로컬 실행 가드 검증 완료. **실제 PostgreSQL에서는 아직 실행하지 않음.**
- smoke는 LEP_MAIL_QA=1, PostgreSQL DB명 mail_review_qa, 기존 테이블이 없는 DB에서만 허용한다. 실제 업무 DB에 실행하지 않는다. DSN/비밀/업무내용 출력·DROP 없음.
- raw UIDL의 `/` 등 경로 문자가 있는 경우 ASGI 단건 경로 라우팅 한계가 남는다. URI 인코딩만으로 해결되지 않을 수 있으며, URL-safe transport 확장은 사용자 중단 지시에 따라 착수하지 않았다.
- Hiworks 미분류 수집은 기존 최근 설정 범위(기본300건) 기준이다. 승인 완료 목록은 DB에서 보존한다.
- 지식화의 볼트 파일쓰기와 DB는 분산 transaction이 아니므로 파일쓰기 후 DB 실패의 완전한 원자성은 별도 후속 범위다.

## 재개 시 최소 순서
1. 아래 최종 검증 결과와 각 WP 문서의 남은 실패/제한부터 확인. 통과한 작업을 재작성하거나 광범위 재점검하지 않는다.
2. 남은 실제 실패만 Claude Code Sonnet medium으로 수정. 기존 세션 resume을 우선해 전체 재독 비용을 줄인다.
3. 이번 메일 변경만 분리한 후보에서 필요한 회귀·빌드 확인. 비밀/임시로그 제외.
4. 격리 PostgreSQL에서 위 smoke 실행 및 additive migration dry-run/apply/reapply 검증.
5. 서버 변경 여부 재확인, 이전 실행 이미지와 원본 파일 복구본 보존 후 배포. 실제 업무 메일 승인/첨부 분류는 사용자가 수행하도록 둔다.

## 임시 산출물
- `.mail-review-runs/`, `.task-runs/`는 gitignored Claude 프롬프트·실행로그·검사 산출물. 제품 배포에 포함하지 않는다.
- `.mail-review-runs/release-src`는 HEAD 원본만 복사한 준비 경로이며 **최종 메일 변경을 overlay하지 않았다. 검증된 배포 후보가 아니다.**
- `.pytest_cache/mail-review-runs`는 Windows ACL 때문에 일반 권한 Claude 실행의 로그 쓰기가 실패했던 경로. 권한 우회/변경 없이 위 대체 경로를 사용했다.

## 최종 동결 검사
코드 작성 종료 후 저장된 checkout을 검사했다. 아래 PASS는 로컬 검증이며 미배포/실제 PostgreSQL 미실행 상태는 그대로다.
### 동결된 frontend 검증 (총괄 실행)
- `corepack pnpm test-unit`: 전체 13파일 **118 passed** (4.08s). 메일 UI93 + 기존 UI25를 포함한다.
- 소유파일 ESLint 및 전체 TypeScript 검사: UI 담당 최종 PASS.
- 잔여: 메일 화면의 `AI 분석` 제목을 실제 키워드 추천에 맞는 `분류 참고`로 정정. 사용자 중단 지시로 추가 코드 호출하지 않았다.

### 비용을 줄이는 Claude 세션 재개
사용자가 다시 요청했을 때만 실행한다. native tool의 session 번호가 아닌 실제 Claude UUID다.
- Backend: `ec4b6fa9-5af9-404a-87c5-77c47fff40a7`
- UI: `f5c98c84-ddd5-44a9-b59c-2739f9c749dc`
- `claude -p --resume <UUID> --model sonnet --effort medium --output-format stream-json --verbose --restricted --tools Read,Glob,Grep,Edit,Write --permission-mode acceptEdits --strict-mcp-config` 형태로 기존 맥락을 재사용한다. 프롬프트는 stdin, 실제 인증정보는 전달하지 않는다.
- 모델 변경/새 에이전트/광범위 전체 재독을 기본으로 하지 않는다. 미해결 항목 하나씩 소유 범위를 고정한다.

- 총괄 최종 frontend build: corepack pnpm build PASS (Next.js 15.4.4, compile/type/lint/static generation 완료). 이 결과는 현재 로컬 checkout 기준이며 메일만 분리한 배포 후보 검증을 의미하지 않는다.
- 사용자 중단 요청에 따라 추가 테스트 확장도 중단하고, 마지막 저장된 backend 상태를 한 번 검사해 인계한다. 자동 재개/추가 에이전트/예약 작업 없음.

### 총괄 최종 backend 및 종료 기록
- `.venv/Scripts/python.exe -m pytest apps/backend/tests -q --basetemp=.mail-review-runs/checks/handoff-full --tb=short`: **299 passed**, 36.15s.
- pytest cache 기록만 Windows ACL 경고1건. 테스트 실패 없음. 이 경고를 고치기 위한 추가 작업은 하지 않았다.
- 최종 Claude backend 호출은 OAuth 세션 만료/refresh 실패로 exit1 종료되었다. 저장된 파일을 위 검사로 검증했으며 인증 재시도·새 모델 호출은 하지 않았다. 향후 Claude 사용 전 인증 복구가 필요할 수 있다.
- 운영 배포, 운영 migration, 실제 PostgreSQL smoke는 실행하지 않았다. 변경은 로컬 미커밋 상태로 보존했다.
- 인계 문서 작성 후 대기한다. 새 사용자 요청 전 자동 재개하지 않는다.

### Backend 최종 담당 검사 / 남은 정확한 항목
- 메일 전용 pytest **52 passed** (14.12s), 소유18파일 mypy PASS, 모듈 경계 PASS.
- **Ruff 미통과1건**: `apps/backend/tests/test_mail_approval.py:1708`, I001 import 정렬. 사용자 중단 지시 및 Claude 인증 만료로 추가 수정 호출하지 않았다. 재개 시 이 작은 항목부터 수정한다.
- 문서 전용37 + 메일전용52 + 기존210 = 총괄 전체299 통과. 프론트 전체118 및 build PASS.
- 모든 하위 작업 동결 완료. 이후 검증/배포를 자동으로 시작하지 않는다.

## 2026-09-09 명시적 재개 및 모델 변경
사용자가 재개를 요청한 뒤 Claude 대신 Luna light를 지정했다. 코드 작성은 gpt-5.6-luna / low로 전환했다. Claude 인증 재시도는 하지 않는다. 잔여 lint·추천 문구·UIDL 특수문자 호환성만 한 에이전트가 처리한다.

격리 검증: 서버 `/tmp/lep-mail-qa-20260909/src`는 원본 HEAD+명시47개 파일로 만든 임시 후보이며 운영 저장소는 clean 상태로 유지했다. 후보 API 이미지 `luminode/api:mail-qa-20260909` 빌드 PASS. 외부 네트워크 없는 임시 PostgreSQL 컨테이너 `lep-mail-qa-db-20260909`의 `mail_review_qa` DB에서 smoke PASS: schema/합성 seed/commit/new-session read/동일 ID 재시도/metadata충돌/추가첨부 기존ID보존/outer rollback/savepoint rollback. 실제 업무 DB나 실제 메일 승인에는 접근하지 않았다.

격리 PostgreSQL migration 검증도 PASS: 기존 실행이미지의 원본 schema를 별도 mail_review_qa_migration DB에 생성한 뒤, 후보 script dry-run은 신규6개만 표시했고 --apply가6개생성, 두번째 --apply는 nothing to do. 임시 QA DB 컨테이너는 확인 후 중지·자동제거했다. 운영 DB/컨테이너는 변경하지 않았다.
