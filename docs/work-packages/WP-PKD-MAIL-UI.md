# WP-PKD-MAIL-UI-20260909 — 메일 승인·첨부 연결 프론트엔드

Work Package ID: WP-PKD-MAIL-UI-20260909
Owned Module: mail_frontend (ADR-021, `docs/work-packages/2026-09-09-mail-approval.md`)
Goal: 자동 분류는 추천으로만 보여주고, 사람이 명시적으로 승인해야 프로젝트/첨부가 확정되는
메일함·드라이브 화면을 만든다.
In Scope: 메일함 탭/카운트/페이지네이션/선택 범위, 승인·제외·추가 첨부 연결 폼과
idempotency, 드라이브의 메일 원본 연결 표시, 첨부 프록시의 안전한 오류/헤더 처리.
Out of Scope: 백엔드 mail/documents 구현(병행 진행 중), 메일 발송/삭제, 일반 업로드·스캔
파이프라인, `gateway.ts`/`actions.ts`/`packages/api-client/src/client.ts`의 기존 계약 변경.
Dependencies: `mail_backend`(`WP-PKD-MAIL-BACKEND.md`)와 `documents_links`
(`WP-PKD-MAIL-DRIVE.md`)가 병행 구현 중인 `/api/v1/mail/*`, `/api/v1/projects/{id}/mail*`,
DriveFile 확장 필드. 이 문서가 가정하는 계약은 `2026-09-09-mail-approval.md`와 사용자
승인 메시지에 적힌 그대로다.
API/Event contracts used:
- `GET /api/v1/projects/{project_id}/mail?status=unclassified|project|unrelated|all&offset=&limit=50`
- `GET /api/v1/projects/{project_id}/mail/counts` → `Envelope[{unclassified,project,unrelated,all}]`
- `POST /api/v1/mail/{id}/approve` `{project_id, expected_version, attachments:[{part_index,category}]}` + `Idempotency-Key`
- `POST /api/v1/mail/{id}/dismiss` `{expected_version}` + `Idempotency-Key`
- `POST /api/v1/mail/{id}/attachments/approve` `{expected_version, attachments:[{part_index,category}]}` + `Idempotency-Key`
- `POST /api/v1/mail/{id}/promote-to-note` → `Envelope[{note_id}]` (계약은 변경 없음; 프론트
  래퍼는 `mail-review-actions.ts`의 `promoteMailToNoteAction`으로 옮겼다 — 아래 참고)
- `GET /api/v1/mail/{id}/attachments/{part}` (기존 프록시가 그대로 호출)

Tables owned: 없음(프론트엔드 전용).
Permissions affected: 없음(서버가 최종 판단). UI는 `can_review`/역할에 따라 편의상
버튼·폼을 숨기거나 비활성화할 뿐이다.
Migration needed: 없음.
Tests required: 아래 "테스트" 절 참고. 코디네이터가 실행한다.
Risks/assumptions: 아래 "가정과 한계" 절 참고.

## 구현

### 계약 타입 (`packages/api-client/src/domain.ts`)

Mail/Drive 필드만 추가했다. 기존 AI·메일 계약 필드는 보존했다.

- `MailAttachment.linked_file_id: string | null`
- `MailMessage.suggested_project_id/version/approved_by/approved_at/can_review`
- 신규 `MailStatusFilter`, `MailCounts`
- `DriveFile.source_mail_id/source_part_index/source_kind/sha256`

### 데이터 계층

- `apps/web/src/shared/data/mail-review.ts` — 새 메일함 전용 조회 헬퍼
  (`fetchMailPage`, `fetchMailCounts`, `normalizeMailStatus`, `normalizeMailPage`,
  `mailOffset`, `MAIL_PAGE_SIZE`). `gateway.ts`의 `listMail`/`getMail`은 옛 계약을
  쓰는 코드가 남아 있을 수 있어 손대지 않고 별도 파일로 분리했다.
- `apps/web/src/shared/data/mail-review-actions.ts` — `approveMailAction`,
  `dismissMailAction`, `approveMailAttachmentsAction`, `promoteMailToNoteAction` 서버
  액션. 각각 백엔드가 요구하는 본문과(승인/제외/추가연결은) `Idempotency-Key` 헤더를
  그대로 보내고, 성공 시에만 관련 경로(메일함/드라이브/볼트/홈)를 `revalidatePath`한다.
  실패를 성공으로 표시하지 않는다(`ok/status/message/traceId/mail` 형태로 그대로 반환).
  성공 검증은 `data.id` 신원 일치만으로 끝내지 않고 작업별로 상태 전이를 다시 확인한다:
  최초 승인은 `classification==="project"` && `project_id===요청한 대상` &&
  `version>expected_version` && `approved_by`/`approved_at` 값 있음 && 선택한 첨부마다
  응답에 `linked_file_id`가 붙어 있음을 요구하고, 첨부 추가 연결은 승인자 확인만 뺀
  같은 조건을, 제외는 `classification==="unrelated"` && 버전 증가만 요구한다. 이 중
  하나라도 어긋나면(잘못된 상태·버전·대상·malformed 200 포함) 성공으로 보지 않고
  `revalidatePath`도 호출하지 않는다. 동일 idempotency key로의 재시도는
  `expected_version`이 그대로이므로 버전 조건을 여전히 만족한다. 재검증에 쓰는
  프로젝트 ID들은 모두 `encodeURIComponent`로 감싸 경로에 넣는다.
- `promoteMailToNoteAction(projectId, messageId)` — 지식화(promote-to-note)도 이제 이
  파일에서 자체 계약으로 다룬다(본문 없이 POST, `data.note_id`가 비어있지 않은 문자열일
  때만 성공, 성공 시 메일함/볼트/홈을 `revalidatePath`). `ActionButton`이 기대하는
  `{ok, message, traceId?}` 형태를 그대로 만족하므로 기존 `actions.ts`의
  `ActionResult`와 구조적으로 호환된다. 승인 게이트(미승인 메일 거부)는 백엔드가
  강제하며, 이 액션은 그 오류(409/403 ProblemDetails)를 그대로 전달할 뿐이다.
  `actions.ts`의 옛 `promoteMailAction`/`dismissMailAction`은 여전히 다른 화면이 참조할
  수 있어 손대지 않았다.

### 화면

- `apps/web/app/(app)/projects/[projectId]/mail/page.tsx` — 탭(`status`)·페이지(`page`)·
  선택 메일(`mail`)을 URL에 반영한다. `status`/`page`는 안전하게 정규화한다. Hiworks
  목록 조회는 TOP200 미리보기라 첨부/본문이 잘려 있을 수 있으므로, **화면에 실제로
  렌더하는 상세는 목록에 있든(기본 첫 건 포함) 없든(드라이브 출처 딥링크) 항상
  `fetchMailById` 단건 조회 결과만 쓴다.** 목록 안 선택은 응답이 지금 탭/역할 범위에
  여전히 속하는지(`project`→분류=project && project_id=현재 프로젝트, `unclassified`/
  `unrelated`→admin && 해당 분류, `all`→admin && 위 셋 중 하나) 다시 검증하고, 목록
  밖(딥링크)은 `classification==="project" && project_id===현재 프로젝트`만 인정한다.
  단건 조회 결과의 `id`가 요청한 ID와 다르거나, 범위 검증에 실패하거나, 조회 자체가
  실패하면 안전한 오류만 보여주고 목록의 다른 메일로 대체하지 않는다(ADR-021). 목록이
  비어 있어도 딥링크 대상이 승인된 소스면 단건 조회는 그대로 시도한다. admin은 탭
  4개(미분류/분류완료/제외됨/전체)와 건수를, 비admin은 탭 없이 `project` 상태 하나만
  본다. 건수 집계(`fetchMailCounts`)는 POP3를 거칠 수 있어 실패할 수 있으므로 목록/
  프로젝트 선택지 조회와 별도로 잡아낸다 — 실패해도 목록·상세·승인 폼은 그대로 보여주고
  제목 옆에 "건수를 확인할 수 없습니다"만 표시한다(탭에는 숫자를 아예 안 붙인다; 0을
  지어내지 않는다). 403은 화면 전체를 갈아치우지 않고 `ForbiddenState`로 본문에
  표시한다. 추천 분류(`intent`/`confidence`)와 승인 상태(`approved_by`/`approved_at`)는
  서로 다른 배지로 분리해 추천이 승인이 아님을 명확히 한다. 첨부는 `linked_file_id`가
  있거나(연결 완료) admin이 미분류 메일을 미리보기할 때만 다운로드 링크를 준다. 그
  외에는 파일명만 보여주고 링크를 만들지 않는다.
- `apps/web/app/(app)/projects/[projectId]/drive/page.tsx` — `source_kind ===
  "mail_attachment"`인 파일에 `DriveMailLink`를 붙여 출처 메일 링크와 다운로드 링크를
  보여준다. 다른 파일 행은 그대로 둔다.
- `apps/web/app/api/mail/[messageId]/attachments/[index]/route.ts` — 404(원본 삭제
  가능성)·409(승인 당시 checksum과 불일치)·403·기타 오류를 각각 한국어로 구분해
  안내하고 상태 코드를 그대로 보존한다. 네트워크 실패는 502로 응답한다. 성공 응답은
  허용 헤더만 옮기고 `content-disposition`이 없으면 `attachment`를 강제하며,
  `x-content-type-options: nosniff`와 `cache-control: private, no-store`를 추가한다.
  업스트림의 `set-cookie` 등은 옮기지 않는다.

### 위젯 (`apps/web/src/widgets/mail/`)

- `MailApprovalForm` — 대상 프로젝트 기본값 없음(빈 선택), 첨부 전부 기본 미선택,
  선택한 첨부만 분류 드롭다운(기본 `original`) 노출. "승인 내용 확인" 요약을 거쳐야
  최종 확인 체크박스가 나타나고, 체크해야 "메일 승인" 버튼이 활성화된다. 대상
  프로젝트·첨부 선택·분류를 바꾸면 idempotency key를 새로 만들고 요약/확인 상태를
  초기화한다. 요약 확인 자체나 실패 후 같은 입력으로 재시도할 때는 key를 유지한다.
  성공하면 key를 새로 만들고 선택을 비운다. `can_review`가 거짓이거나 이미 분류된
  메일이면 아무것도 렌더하지 않는다.
- `MailDismissButton` — 명시적 확인 체크박스에 동의해야 제외 버튼이 활성화된다.
  `expected_version`과 idempotency key를 그대로 액션에 넘긴다.
- `MailAttachmentFollowupForm` — 이미 승인된 메일(`classification==="project"`)에서
  `linked_file_id`가 없는 첨부만 선택지로 보여준다(대상 프로젝트는 절대 바꾸지 않음).
  최소 1개 선택을 요구하며, 선택할 새 첨부가 없거나 아직 승인되지 않은 메일이면
  렌더하지 않는다.
- `DriveMailLink` — `source_mail_id`/`source_part_index`가 없으면 로컬에 파일이 있는
  척 링크를 만들지 않고 "확인할 수 없습니다"만 보여준다. 메일함 링크는 항상 현재
  프로젝트의 `?status=project&mail=<id>&linked_file_id=<file.id>`로 보낸다. 목록
  페이지네이션 범위 밖의 메일이어도, 승인되어 현재 프로젝트로 확정된 소스 메일이면
  메일함이 단건 조회로 그 딥링크를 보여준다(임의 메일 ID를 조회하게 허용하는 것은
  아니다 — `mail/page.tsx`가 classification/project_id를 다시 검증한다). 링크에 실는
  `projectId`도 `encodeURIComponent`로 감싼다.

## 테스트 (작성자는 미실행, 조정자 검증 결과는 마지막 인계 절 참조)

모두 `apps/web/src/widgets/mail/*.test.ts(x)`에 있다(vitest include 경로가
`src/**/*.test.tsx`만 보므로 `app/api` 아래 라우트 테스트도 이 경로에 배치하고
모듈을 직접 import했다).

- `mail-review.test.ts` — 상태/페이지 정규화, offset/limit 쿼리, 세션 쿠키 전달.
- `mail-review-actions.test.ts` — approve/dismiss/attachments-approve의 정확한
  엔드포인트·본문·`Idempotency-Key`·쿠키, 409/네트워크 실패 처리, 성공 시에만
  `revalidatePath` 호출.
- `mail-attachment-proxy.test.ts` — 404/409/502 상태 보존과 한국어 안내, 성공 응답의
  허용 헤더만 전달·`nosniff`·`no-store`·`set-cookie` 미전달.
- `MailApprovalForm.test.tsx` — 기본 빈 선택, 요약 전 제출 차단, 정확한 payload,
  재시도 시 key 유지·입력 변경 시 key 교체, 첨부 0개(메일만 승인) 유효성, 렌더 조건.
- `MailDismissButton.test.tsx` — 확인 전 비활성화, payload, 409 비성공 처리.
- `MailAttachmentFollowupForm.test.tsx` — 이미 연결된 첨부 제외, 최소 1개 선택 요구,
  정확한 payload, 렌더 조건.
- `DriveMailLink.test.tsx`, `DrivePageMailLink.test.tsx` — 출처 링크 표시, 출처 정보
  없을 때 가짜 링크 금지, 일반 파일에는 아무것도 추가하지 않음.
- `MailPage.test.tsx` — admin 탭/건수, nonadmin 탭 숨김과 `project` 고정, 목록 밖 딥링크
  단건 재검증, 페이지네이션 표시, 403 처리, 지식화 버튼 활성/비활성 사유, 목록
  미리보기보다 많은 첨부를 가진 단건 상세가 실제로 렌더/선택되는지(11번 조항), 건수
  조회 실패에도 목록·상세가 살아남는지(12번 조항).

## 가정과 한계

- 백엔드(`mail_backend`, `documents_links`)가 병행 구현 중이라 실제 API 응답으로 검증하지
  못했다. 이 화면은 작업 지시서의 계약 문구를 그대로 구현했으며, 백엔드가 다른 필드명/
  오류 코드를 내면 조정이 필요하다.
- `GET /api/v1/mail/{id}` 단건 조회를 이제 항상 쓴다(최초에는 목록 응답이 상세 렌더에
  필요한 필드를 모두 갖고 있다고 가정해 쓰지 않았으나, Hiworks 목록이 TOP200 미리보기라
  첨부가 잘릴 수 있음이 드러나 정정했다). 목록 응답은 이제 왼쪽 목록 패널의 미리보기
  용도로만 쓰고, 실제로 렌더하는 상세·승인 폼·첨부 목록은 전부 단건 조회 결과다. 그만큼
  선택이 바뀔 때마다 추가 요청이 하나 더 나간다(목록/건수/프로젝트 조회와는 병렬화하지
  않는다 — 목록 결과 안에 있는 ID인지부터 알아야 하므로).
- `MailAttachmentFollowupForm`을 `MailApprovalForm`과 나란히 항상 렌더하도록 두었다.
  둘 다 내부 조건에서 스스로 `null`을 반환하므로 화면에는 항상 최대 하나만 보이지만,
  "승인 폼"과 "추가 연결 폼"이 조건상 동시에 켜질 수 있는 상태(예: 서버가 승인 직후에도
  `can_review=true`이고 `classification`이 아직 `unclassified`로 보이는 경우)가 있다면
  두 폼이 함께 나타날 수 있다. 백엔드 상태 전이가 확정되면 재검증이 필요하다.
- admin의 `unclassified`/`unrelated`/`all` 탭이 실제로 프로젝트 무관 공용 검토함을
  반환하는지는 백엔드 구현에 달려 있다. 프론트는 현재 프로젝트 경로로 상태만 바꿔
  요청할 뿐, 공유 범위 자체는 서버가 결정한다(ADR-020 미승인 정책과는 무관).
- 이 세션은 Read/Glob/Grep/Edit/Write만 사용했다. `npm`/`vitest`/타입체크를 실행하지
  않았으므로 타입 오류나 테스트 실패 가능성을 배제할 수 없다. 코디네이터의 실행 결과를
  기준으로 삼아야 한다.
- Tailwind 임의 클래스(`text-success-ink`, `text-danger-ink` 등)는 기존 화면
  (`ActionButton`, `CreateProjectForm`)이 쓰는 것과 같은 이름을 그대로 재사용했다. 새
  토큰을 추가하지 않았다.

## 완료 보고

Completed Work Package: WP-PKD-MAIL-UI-20260909
Files/Modules changed:
- `packages/api-client/src/domain.ts`
- `apps/web/src/shared/data/mail-review.ts` (신규)
- `apps/web/src/shared/data/mail-review-actions.ts` (신규)
- `apps/web/app/(app)/projects/[projectId]/mail/page.tsx`
- `apps/web/app/(app)/projects/[projectId]/drive/page.tsx`
- `apps/web/app/api/mail/[messageId]/attachments/[index]/route.ts`
- `apps/web/src/widgets/mail/MailApprovalForm.tsx` (신규)
- `apps/web/src/widgets/mail/MailDismissButton.tsx` (신규)
- `apps/web/src/widgets/mail/MailAttachmentFollowupForm.tsx` (신규)
- `apps/web/src/widgets/mail/DriveMailLink.tsx` (신규)
- `apps/web/src/widgets/mail/*.test.ts(x)` (신규, 위 "테스트" 절 목록)
- 본 문서

Behavior delivered: ADR-021이 요구하는 추천/승인 분리, 미선택 기본값, 명시적 요약·확인,
idempotency 재시도/신규 key 규칙, 승인 후 후속 첨부 연결, 메일 원본 드라이브 링크,
안전한 첨부 프록시 오류 처리.
API/Event contracts: 위 "API/Event contracts used" 절과 동일. 이벤트 발행 없음.
Migrations: 없음.
Permissions/Audit: 서버 판단을 UI가 대체하지 않음. `can_review`/역할로 편의상 폼을 숨기되
서버 403은 별도로 처리.
Tests run and results: 이 세션에서 실행하지 않았다(Bash 금지 범위). 코디네이터가
`apps/web`에서 vitest를 실행해야 한다.
Known limitations: 위 "가정과 한계" 절 참고.
Follow-up dependencies: `mail_backend`/`documents_links`의 실제 계약 확정과 통합 검증.

## 후속 계약 수정 (2026-09-09, ADR-021 필수 amendments)

조정자가 제시한 10개 필수 후속 조항을 모두 반영했다. 테스트는 각 조항의 회귀
케이스를 구현 전에 작성했고(코디네이터가 실행), 이 세션에서 직접 실행하지는
않았다.

1. **목록 밖 승인 소스 딥링크** — `mail-review.ts`에 `fetchMailById` 추가.
   `mail/page.tsx`는 URL의 `mail`이 현재 페이지 목록에 없으면 단건 조회 후
   `classification==="project" && project_id===현재 프로젝트`를 독립적으로
   재검증한다. 실패(다른 프로젝트/미승인/조회 실패)하면 목록의 다른 메일로
   대체하지 않고 인라인 오류만 보여준다. `MailPage.test.tsx`에 승인된
   목록 밖 케이스, 다른 프로젝트/미승인 거부 케이스, 조회 실패 케이스를
   추가했다.
2. **다운로드 URL의 `linked_file_id` 쿼리** — `DriveMailLink`의 다운로드/출처
   링크와 `mail/page.tsx`의 연결된 첨부 링크 모두 `?linked_file_id=<DriveFile.id>`를
   붙인다. 대기중 admin 미리보기(미연결 첨부)는 이 쿼리를 붙이지 않는다.
   `apps/web/app/api/mail/[messageId]/attachments/[index]/route.ts`는
   `linked_file_id` 쿼리만 URL-encode해서 업스트림에 전달하고, 그 외 쿼리는
   버린다.
3. **첨부 추가 승인 폼 조건** — 기존 `MailAttachmentFollowupForm` 조건
   (`admin && can_review && classification==="project" && 미연결 첨부 있음`)이
   이미 이 조항을 만족해 별도 코드 변경은 없었다.
4. **counts는 기존 ListMeta만 사용** — `fetchMailPage`가 이미
   `meta.total`/`meta.has_more`만 쓰고 있어 변경 없음.
5. **출처 메일 링크의 `linked_file_id` 검증** — `DriveMailLink`의 메일함 링크도
   `linked_file_id`를 함께 싣는다. `mail/page.tsx`는 프로젝트/분류 검증 뒤,
   `linked_file_id`가 쿼리에 있으면 선택된 메일의 `attachments[].linked_file_id`
   중 일치하는 게 있는지 확인하고, 없으면 "원본 소스를 사용할 수 없습니다"로
   표시한다(대체 메일 없음). 일반 탭/페이지 이동 링크는 이 쿼리를 붙이지 않으므로
   자연히 사라진다.
6. **SSR 병렬화** — `mail/page.tsx`는 `gateway.me()`로 역할만 먼저 확인하고,
   `fetchMailPage`/`fetchMailCounts`/`gateway.listProjects()`를 `Promise.all`로
   병렬 실행한다(이전에는 `listProjects`가 목록 완료 후 순차 호출됐다). 목록 밖
   딥링크 단건 조회는 목록 결과가 필요할 때만(목록에 없을 때만) 뒤따른다.
7. **드라이브 페이지네이션** — `mail-review.ts`에 `fetchDriveFilesPage`/
   `normalizeDriveOffset`/`DRIVE_PAGE_SIZE`를 추가해 `ListEnvelope`의
   `total`/`has_more`를 보존한다(`gateway.listDriveFiles`는 이를 버린다).
   `drive/page.tsx`는 이 헬퍼로 바꾸고 `offset` 쿼리를 0 이상 정수로 정제하며,
   이전/다음 링크는 분류를 유지한 채 ±50 이동하고, 분류를 바꾸는 링크는 `offset`
   쿼리를 아예 생략해 1쪽으로 되돌아간다.
8. **액션 응답 검증 강화** — `mail-review-actions.ts`의 `toResult`는 이제
   `expectedMessageId`를 받아 성공 응답의 `data.id`가 비어있지 않고 요청한
   메일과 같을 때만 성공으로 본다(신원 일치, 최소 검증). 실패 응답은
   `code`/`status`/`title`이 모두 있고 `detail`/`trace_id`가 있다면 문자열인
   RFC 7807 형태일 때만 `detail`/`title`/`trace_id`를 쓰고, 아니면 임의 본문을
   노출하지 않는 일반 오류 메시지로 대체한다. `approve`/`dismiss`/
   `attachments/approve` 경로 세그먼트의 `messageId`를 모두
   `encodeURIComponent`로 감쌌다.
9. **폼 로컬 상태 격리 및 편집 잠금** — `mail/page.tsx`는 승인/제외/추가연결
   폼을 `message.id:message.version` 키의 `Fragment`로 감싸 다른 메일/버전으로
   전환될 때 리액트가 로컬 상태를 새로 만들게 했다. 세 폼 모두 `pending` 동안
   대상 프로젝트 선택/첨부 체크박스/분류 드롭다운/최종 확인 체크박스를
   `disabled`로 잠가, 전송 중 편집으로 방금 성공한 요청의 입력이 지워지는
   경합을 막았다.
10. **TDD 이력 관련** — 이번 세션은 각 조항의 회귀 테스트를 먼저 작성한 뒤
    구현했다. 최초 구현 단계의 이력(위젯이 테스트보다 먼저 나온 것으로 보였던
    부분)은 정정하지 않고 그대로 둔다(이미 벌어진 일을 다시 쓰지 않는다).

### 코디네이터가 관찰한 초기 실패 수정

- `mail-attachment-proxy.test.ts`의 한글 파일명 테스트가 원본 한글을
  `content-disposition` 헤더 값에 그대로 넣어 `Headers` 생성자가 던지는
  문제를 고쳤다. 이제 실제 백엔드 계약대로 `filename*=UTF-8''` RFC5987
  인코딩된 값을 쓰고, 인코딩된 한글 파일명이 포함되는지 확인한다.
- `MailApprovalForm.test.tsx`의 재시도 테스트가 실패 후에도 여전히 체크된
  확인 체크박스를 한 번 더 클릭해 오히려 해제시키던 문제를 고쳤다. 실패 후
  같은 입력으로 재시도할 때는 체크박스를 다시 누르지 않고, 입력을 바꾸는
  블록에서만 다시 확인 절차를 거치도록 테스트를 정정했다. 컴포넌트는 전송
  실패 시 `confirmed`/`reviewed`/key를 초기화하지 않는 기존 동작을 유지한다.
- `mail-review-actions.test.ts`의 `vi.mock("next/cache", ...)`가 호이스팅된
  팩토리 안에서 아직 초기화되지 않은 `const`를 참조하던 문제를 `vi.hoisted`로
  고쳤다.
- `DrivePageMailLink.test.tsx`는 이미 `afterEach(() => cleanup())`이 있었다.
  다만 `gateway.listDriveFiles` 대신 새 `fetchDriveFilesPage` 헬퍼를 쓰도록
  모킹 대상을 바꿨다(7번 조항).

## 최종 리뷰 반영 (2026-09-09, 마지막 배치)

11. **첨부 전체 조회(치명적 기능 결함)** — Hiworks 목록은 TOP200 미리보기라 첨부가
    잘려 있을 수 있는데, `mail/page.tsx`가 목록 응답(`inPageMatch`/`messages[0]`)을
    그대로 상세로 렌더해 뒤쪽 MIME 첨부를 조용히 빠뜨리고 있었다. 이제 선택된 메일이
    무엇이든(기본 첫 건/목록 내 선택/목록 밖 딥링크) 항상 `fetchMailById`로 전체
    상세를 다시 받아 `detail.id===요청 ID`를 먼저 확인하고, 목록 안이면 지금
    탭(status)/역할 범위에 여전히 속하는지(`canViewWithinTab`), 목록 밖이면 여전히
    `classification==="project" && project_id===현재 프로젝트`인지 검증한 뒤에만
    화면·승인 폼·첨부 목록에 쓴다. 실패하면 안전한 오류만 보여주고 목록 미리보기로
    대체하지 않는다. `MailPage.test.tsx`에 목록 미리보기(첨부 1개)와 전체 상세(첨부
    2개)를 구분해 두 번째 첨부의 체크박스/선택이 실제로 동작하는지 확인하는 회귀
    테스트를 추가했고, 기존 픽스처들은 전부 `fetchMailById`가 그 메일의 전체 상세를
    돌려주도록 갱신했다.
12. **건수 조회 실패 복원력** — 승인된 프로젝트 목록은 DB 기반이지만 건수 집계는
    POP3를 거칠 수 있어 실패할 수 있다. `fetchMailCounts` 호출을 `Promise.all` 안에서
    별도로 `.then(ok, fail)`로 감싸 그 실패가 목록/프로젝트 선택지 조회 전체를
    무너뜨리지 않게 했다. 실패하면 탭에는 숫자를 붙이지 않고(가짜 0을 보여주지 않음)
    제목 옆에 "건수를 확인할 수 없습니다"만 표시하며, 목록/상세/승인 폼은 정상 노출된다.
    목록 조회 자체의 실패는 여전히 화면 전체 오류로 처리한다(이건 admin 검토 대상
    선택에 필수라 건수와 다르게 다뤄야 한다).
13. **작업별 성공 재검증** — `mail-review-actions.ts`의 `toResult`가 `data.id` 신원
    일치만 보던 것을 작업별 상태 전이 검증으로 강화했다(위 "데이터 계층" 절 참고).
    409 오류 픽스처도 `code`/`status`/`title`을 모두 갖춘 진짜 ProblemDetails 형태로
    바꿨다(예전 `detail`만 있는 픽스처는 우연히 안전한 일반 오류로 떨어졌을 뿐 실제
    계약을 검증하지 못했다).
14. **지식화 액션 이전** — `promoteMailAction`(옛 `actions.ts`, `messageId`를
    URL-encode하지 않고 재검증도 하지 않음)을 이 화면에서 더 이상 쓰지 않는다.
    `mail-review-actions.ts`의 `promoteMailToNoteAction`으로 옮기고 `mail/page.tsx`의
    `ActionButton`이 이걸 부르도록 바꿨다. `actions.ts`는 다른 화면이 참조할 수 있어
    그대로 뒀다(중복 제거를 이 화면 책임 밖까지 확장하지 않음).
15. **경로 세그먼트 escape 일관성** — 메일 ID뿐 아니라 프로젝트 ID도 경로에 넣을 때는
    전부 `encodeURIComponent`로 감쌌다: `mail-review.ts`의 `fetchMailPage`/
    `fetchMailCounts`/`fetchDriveFilesPage`, `mail-review-actions.ts`의 모든
    `revalidatePath` 대상, `DriveMailLink`의 메일함 링크.
16. **DrivePageMailLink 테스트 정정** — "일반 파일은 메일 링크를 만들지 않는다"
    테스트가 `screen.queryByRole('link')`로 문서 전체를 봐서, 분류 탭 자체가
    `Link`인 것과 우연히 충돌해 항상 실패했다(진짜 결함은 아니었다). 파일 행으로
    범위를 좁혀 "출처 메일 보기"/"다운로드" 링크가 그 행에 없는지, 분류 탐색 링크는
    건드리지 않고 확인하도록 고쳤다.


## 2026-09-09 중단·인계

사용자 요청에 따라 진행 중이던 마지막 Claude 호출까지 종료하고 코드를 동결했다. 이 기록은 전체 배포/운영 완료 선언이 아니다.

- 구현: 모든 선택 메일 full 상세 조회(TOP200 목록 요약 대체), 탭·프로젝트·ID·출처 linked_file_id 검증, 건수 조회 실패 격리, 작업별 승인 성공 상태/버전/연결 검증, note_id 확인 지식화, 첨부 추가승인, 드라이브 페이지 이동.
- 검증: `corepack pnpm --filter @lep/web exec vitest run src/widgets/mail` → 9 files, 93 passed (2.83s); `corepack pnpm typecheck` → 통과; 소유 mail/drive pages, proxy, widgets/mail, mail-review helpers ESLint → 통과(eslintrc 모드). 운영 메일·파일 조회 없이 fixture만 사용했다. 총괄이 빌드를 별도 수행한다.
- 변경 파일: Mail/Drive 타입(`packages/api-client/src/domain.ts`), 메일·드라이브 page, attachment proxy, 신규 `src/shared/data/mail-review.ts`/`mail-review-actions.ts`, 신규 `src/widgets/mail` 컴포넌트 4개·테스트 9개, 이 문서. 기존 AI/메일첨부 및 타 모듈 변경은 유지했다.
- 남은 필수 문구: 메일 페이지 `AiPanel title="AI 분석"`을 실제 발신정보·키워드 규칙에 맞는 `분류 참고`로 바꾸고 추천은 미승인임을 안내해야 한다. 중단 요청 후 새 Claude 호출하지 않아 미반영이다.
- 후속 검토 메모: action 성공 validator의 version은 현재 number 및 증가 여부만 검사한다. safe integer 검사와 malformed attachments 배열에 대한 명시적 false 처리를 보강할 수 있다(현재 잘못된 배열은 guard에서 오류가 되어 성공으로 표시되지는 않음). 운영 통합·실사용 첨부·브라우저 검증 및 배포는 조정자 후속 범위다.
- Claude 재개 session_id: `f5c98c84-ddd5-44a9-b59c-2739f9c749dc` (도구 실행 ID 59552와 다름). 실제 작성 모델 `claude-sonnet-5` (`--model sonnet --effort medium`). 재개 시 `--resume f5c98c84-ddd5-44a9-b59c-2739f9c749dc --model sonnet --effort medium`으로 문맥 재사용 가능. 지금 추가 호출하지 않았다.
- 로그: `.mail-review-runs/frontend-final.jsonl`; 테스트: `.mail-review-runs/frontend-tests-handoff.txt`; 미반영 메모: `.mail-review-runs/frontend-last-notes.md`. 로그 디렉터리는 임시 산출물이므로 총괄 정리·보관 정책에 따른다.
