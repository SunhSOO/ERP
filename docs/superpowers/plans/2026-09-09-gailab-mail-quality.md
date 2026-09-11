# GAILAB 브랜딩 및 메일 품질 개선 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 사용자 노출 브랜드를 GAILAB으로 바꾸고, 메일 상세·첨부 다운로드를 안정화하며 프로젝트 맥락 기반 분류 추천을 제공한다.

**Architecture:** 메일 추천은 mail application 계층의 순수 점수 계산으로 제공한다. projects 모듈은 읽기 전용 공개 인터페이스로 프로젝트 맥락을 제공하고, mail 서비스가 미분류 메일과 승인 이력을 조합해 응답 전용 추천을 만든다. 추천은 승인 상태나 DB 데이터를 쓰지 않으며 기존 API에 선택적 필드를 추가한다.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy, Next.js 15, React 19, TypeScript, Vitest, pytest.

**Spec:** `docs/superpowers/specs/2026-09-09-gailab-mail-quality-design.md`

## Global Constraints

- 코드 작성·수정은 Claude Haiku 4.5 medium만 사용한다.
- 사용자 노출 `Luminode`만 `GAILAB`으로 바꾸며 `LEP_*`, `@lep/*`, Docker Compose/이미지/볼륨/서버 경로는 유지한다.
- 추천은 `unclassified` 상태를 바꾸지 않고, 관리자 승인·버전·idempotency·감사는 기존 경로를 유지한다.
- 추천은 프로젝트 공개 인터페이스와 mail-owned 데이터만 읽고 다른 모듈 테이블에 직접 접근하지 않는다.
- migration, 실제 업무 메일 조회·승인·대량 재분류는 하지 않는다.
- 새 동작마다 실패하는 테스트를 먼저 확인하고 최소 구현 후 같은 테스트를 통과시킨다.

---

### Task 1: 사용자 노출 브랜드를 GAILAB으로 변경

**Files:**
- Modify: `apps/web/app/layout.tsx:5-6`
- Modify: 사용자 화면에서 직접 노출되는 `Luminode` 문자열이 있는 파일
- Modify: `README.md:1`, `docs/design/CLAUDE_DESIGN_BRIEF.md:1,6`
- Test: `apps/web/app/layout.test.tsx` (새 파일)

**Interfaces:**
- Consumes: Next.js `Metadata`, `RootLayout`.
- Produces: 브라우저 제목과 사용자 문서의 `GAILAB` 표기. 내부 `LEP`·`luminode` 식별자는 변경하지 않음.

- [ ] **Step 1: 메타데이터의 현재 브랜드를 검증하는 실패 테스트를 작성한다.**

```tsx
import { expect, it } from "vitest";
import { metadata } from "./layout";

it("publishes GAILAB as the user-facing application title", () => {
  expect(metadata.title).toBe("GAILAB ERP Platform");
  expect(metadata.description).toContain("GAILAB");
});
```

- [ ] **Step 2: 테스트가 기존 `Luminode` 제목 때문에 실패하는지 확인한다.**

Run: `corepack pnpm --filter @lep/web exec vitest run app/layout.test.tsx`

Expected: `metadata.title`가 `Luminode ERP Platform`이라 실패.

- [ ] **Step 3: 메타데이터와 사용자 문서의 표기를 최소 변경한다.**

```ts
export const metadata: Metadata = {
  title: "GAILAB ERP Platform",
  description: "GAILAB ERP foundation shell",
};
```

`rg -n -i "luminode" apps/web README.md docs/design` 결과 중 사용자 노출 문구만 변경한다. `infra/`, 패키지명, 환경 변수, 이미지명은 수정하지 않는다.

- [ ] **Step 4: 브랜드 테스트와 기존 웹 테스트를 통과시킨다.**

Run: `corepack pnpm --filter @lep/web exec vitest run app/layout.test.tsx`

Expected: PASS.

- [ ] **Step 5: 이 작업 파일만 커밋한다.**

```bash
git add apps/web/app/layout.tsx apps/web/app/layout.test.tsx README.md docs/design/CLAUDE_DESIGN_BRIEF.md
git commit -m "feat: rename user-facing brand to GAILAB"
```

### Task 2: 첨부 파일의 파일명과 확장자를 모든 브라우저에 보존

**Files:**
- Modify: `apps/backend/src/lep/modules/mail/api/routes.py:65-78,359-394`
- Modify: `apps/backend/tests/test_mail_approval.py`
- Modify: `apps/web/src/widgets/mail/mail-attachment-proxy.test.ts`
- Modify only if test shows loss: `apps/web/app/api/mail/[messageId]/attachments/[index]/route.ts`

**Interfaces:**
- Consumes: `MailReviewService.fetch_attachment() -> tuple[str, str, bytes]`.
- Produces: `Content-Disposition: attachment; filename="attachment.pdf"; filename*=UTF-8''%EA...`.
- Compatibility: UTF-8 `filename*` keeps the original name; ASCII `filename` fallback keeps the original safe extension.

- [ ] **Step 1: API가 한글 이름과 `.xlsx` 확장자를 가진 두 filename 파라미터를 보내야 한다는 실패 테스트를 작성한다.**

```python
response = client.get(f"/api/v1/mail/{message_id}/attachments/0")
assert response.status_code == 200
disposition = response.headers["content-disposition"]
assert 'filename="attachment.xlsx"' in disposition
assert "filename*=UTF-8''" in disposition
assert urllib.parse.quote("검토 자료.xlsx") in disposition
```

- [ ] **Step 2: 기존 헤더에 ASCII fallback이 없어서 실패하는지 확인한다.**

Run: `.venv/Scripts/python.exe -m pytest apps/backend/tests/test_mail_approval.py -q -k "attachment and disposition" --tb=short`

Expected: `filename="attachment.xlsx"` assertion failure.

- [ ] **Step 3: 안전한 ASCII fallback을 생성하고 기존 UTF-8 파일명을 유지한다.**

```python
def _filename_fallback(filename: str) -> str:
    suffix = Path(_sanitize_filename(filename)).suffix
    return f"attachment{suffix[:16]}" if suffix else "attachment"

headers = {
    "content-disposition": (
        f'attachment; filename="{_filename_fallback(filename)}"; '
        f"filename*=UTF-8''{quoted}"
    ),
    "X-Content-Type-Options": "nosniff",
}
```

`Path` suffix는 안전한 파일명에서만 사용하며 CR/LF, 경로 구분자, 비정상 MIME 값은 기존 sanitizer를 우회하지 않는다.

- [ ] **Step 4: 웹 프록시가 두 filename 파라미터를 바꾸지 않는 실패 테스트를 추가한다.**

```ts
expect(response.headers.get("content-disposition")).toBe(
  `attachment; filename="attachment.xlsx"; filename*=UTF-8''${encodeURIComponent("검토 자료.xlsx")}`,
);
```

- [ ] **Step 5: API·프록시 테스트를 통과시킨다.**

Run: `.venv/Scripts/python.exe -m pytest apps/backend/tests/test_mail_approval.py -q --tb=short`

Run: `corepack pnpm --filter @lep/web exec vitest run src/widgets/mail/mail-attachment-proxy.test.ts`

Expected: PASS.

- [ ] **Step 6: 이 작업 파일만 커밋한다.**

```bash
git add apps/backend/src/lep/modules/mail/api/routes.py apps/backend/tests/test_mail_approval.py apps/web/src/widgets/mail/mail-attachment-proxy.test.ts
git commit -m "fix: preserve mail attachment extensions on download"
```

### Task 3: 목록에서 선택한 메일 상세의 오탐 접근 거부 수정

**Files:**
- Modify: `apps/web/app/(app)/projects/[projectId]/mail/page.tsx:36-102`
- Modify: `apps/web/src/widgets/mail/MailPage.test.tsx`
- Modify: `apps/web/src/widgets/mail/MailPage.loading.test.tsx`
- Test: `apps/backend/tests/test_mail_approval.py` (기존 권한 거부 회귀 확인)

**Interfaces:**
- Consumes: `fetchMailPage()`, `fetchMailById()`, `MailMessage.classification`, backend `GET /api/v1/mail/{id}` authorization.
- Produces: 현재 목록에 있던 메일은 상세 응답이 목록 스냅샷과 달라도 backend가 허용하면 표시; 목록 밖 딥링크는 현재 프로젝트·첨부 연결 검증을 유지.

- [ ] **Step 1: 목록 선택 후 서버가 허용한 최신 상세를 표시해야 한다는 실패 테스트를 작성한다.**

```tsx
mockedFetchMailPage.mockResolvedValue({ messages: [pendingMail], total: 1, hasMore: false });
mockedFetchMailById.mockResolvedValue({ ...pendingMail, classification: "project", project_id: PROJECT_ID });

await renderPage({ mail: pendingMail.id, status: "unclassified" });

expect(await screen.findByRole("region", { name: "메일 상세" })).toHaveTextContent(pendingMail.subject);
expect(screen.queryByText("이 메일을 볼 수 없습니다.")).not.toBeInTheDocument();
```

- [ ] **Step 2: 기존 프런트 상태 검사 때문에 실패하는지 확인한다.**

Run: `corepack pnpm --filter @lep/web exec vitest run src/widgets/mail/MailPage.test.tsx src/widgets/mail/MailPage.loading.test.tsx`

Expected: `이 메일을 볼 수 없습니다.`가 표시되어 실패.

- [ ] **Step 3: 목록 안 선택과 목록 밖 딥링크를 분리한다.**

```ts
if (inPageMatch) {
  return detail; // backend GET already authorizes the current actor
}
if (detail.classification !== "project" || detail.project_id !== projectId) {
  return { error: "forbidden" };
}
// linked_file_id is checked only for an outside-page drive deep link.
```

백엔드 403은 계속 `{ error: "forbidden" }`으로 보이며, `inPageMatch`가 있어도 다른 사용자의 메일을 허용하지 않는다.

- [ ] **Step 4: 다른 프로젝트 딥링크와 non-admin 미분류 거부 테스트가 여전히 통과하는지 확인한다.**

Run: `corepack pnpm --filter @lep/web exec vitest run src/widgets/mail/MailPage.test.tsx src/widgets/mail/MailPage.loading.test.tsx`

Expected: 새 정상 선택 테스트와 기존 보안 테스트 모두 PASS.

- [ ] **Step 5: 이 작업 파일만 커밋한다.**

```bash
git add 'apps/web/app/(app)/projects/[projectId]/mail/page.tsx' apps/web/src/widgets/mail/MailPage.test.tsx apps/web/src/widgets/mail/MailPage.loading.test.tsx
git commit -m "fix: show authorized selected mail details"
```

### Task 4: 프로젝트 맥락 기반 추천 도메인 모델과 점수 계산

**Files:**
- Create: `apps/backend/src/lep/modules/mail/application/recommendations.py`
- Modify: `apps/backend/src/lep/modules/mail/domain/entities.py`
- Modify: `apps/backend/src/lep/modules/projects/public.py`
- Modify: `apps/backend/src/lep/modules/projects/application/services.py`
- Create: `apps/backend/tests/test_mail_recommendations.py`

**Interfaces:**
- Produces: `MailProjectSuggestion(project_id: str, project_name: str, confidence: Confidence, reasons: tuple[str, ...])`.
- Produces: `recommend_projects(message, project_contexts, approved_contexts) -> tuple[MailProjectSuggestion, ...]`.
- Consumes: `ProjectContextRef(id, code, name, customer_name)` exposed by `projects.public.list_project_contexts(db)`.

- [ ] **Step 1: 프로젝트 코드·고객사·마일스톤 조합이 한 프로젝트를 high로 추천한다는 실패 테스트를 작성한다.**

```python
message = _mail(subject="DAON M3 검토 요청", body="다온 정수장 일정 검토", milestone_code="M3")
projects = [
    ProjectContextRef(id="daon", code="PRJ-DAON", name="다온 정수장", customer_name="다온"),
    ProjectContextRef(id="other", code="PRJ-OTHER", name="기타", customer_name="타사"),
]

result = recommend_projects(message, projects, approved_contexts=[])

assert result[0].project_id == "daon"
assert result[0].confidence is Confidence.HIGH
assert "프로젝트명: 다온 정수장" in result[0].reasons
```

- [ ] **Step 2: 테스트가 모듈 부재로 실패하는지 확인한다.**

Run: `.venv/Scripts/python.exe -m pytest apps/backend/tests/test_mail_recommendations.py -q --tb=short`

Expected: `ModuleNotFoundError` 또는 `ImportError`.

- [ ] **Step 3: 결정적 점수 계산을 최소 구현한다.**

```python
def recommend_projects(message, projects, approved_contexts):
    scored = [_score(message, project, approved_contexts) for project in projects]
    ranked = sorted((item for item in scored if item.score > 0), key=lambda item: (-item.score, item.project.id))
    if len(ranked) > 1 and ranked[0].score == ranked[1].score:
        return ()
    return tuple(_to_suggestion(item) for item in ranked[:3])
```

`_score`는 프로젝트 코드·이름·고객사·마일스톤의 대소문자 무시 문자열 일치와 같은 프로젝트의 승인 메일 제목·의도·마일스톤 일치만 점수화한다. 본문에서 짧은 단어 하나만 일치하는 경우에는 low 추천도 만들지 않는다.

- [ ] **Step 4: 동점, 근거 없음, 승인 이력 일치, 도메인 추천과의 호환성 테스트를 추가한다.**

```python
assert recommend_projects(_mail(subject="일반 안내", body=""), projects, []) == ()
assert recommend_projects(_mail(subject="공통 M3", body=""), equally_matching_projects, []) == ()
assert recommend_projects(message, projects, [approved_for_daon])[0].project_id == "daon"
```

- [ ] **Step 5: 순수 추천 테스트를 통과시킨다.**

Run: `.venv/Scripts/python.exe -m pytest apps/backend/tests/test_mail_recommendations.py -q --tb=short`

Expected: PASS.

- [ ] **Step 6: 이 작업 파일만 커밋한다.**

```bash
git add apps/backend/src/lep/modules/mail/application/recommendations.py apps/backend/src/lep/modules/mail/domain/entities.py apps/backend/src/lep/modules/projects/public.py apps/backend/src/lep/modules/projects/application/services.py apps/backend/tests/test_mail_recommendations.py
git commit -m "feat: recommend mail projects from project context"
```

### Task 5: 추천을 메일 API·목록·승인 UI에 연결

**Files:**
- Modify: `apps/backend/src/lep/modules/mail/application/services.py`
- Modify: `apps/backend/src/lep/modules/mail/api/routes.py`
- Modify: `packages/api-client/src/domain.ts`
- Modify: `apps/web/src/shared/data/mail-review.ts`
- Modify: `apps/web/app/(app)/projects/[projectId]/mail/page.tsx`
- Modify: `apps/web/src/widgets/mail/MailDetailSection.tsx`
- Modify: `apps/web/src/widgets/mail/MailApprovalForm.tsx`
- Modify: `apps/web/src/widgets/mail/MailPage.test.tsx`
- Modify: `apps/web/src/widgets/mail/MailPage.loading.test.tsx`
- Modify: `apps/backend/tests/test_mail_approval.py`

**Interfaces:**
- Adds optional `suggestions: MailProjectSuggestion[]` to `MailOut` and TypeScript `MailMessage`.
- Adds optional `suggested=yes|no` only to `GET /api/v1/projects/{project_id}/mail?status=unclassified`.
- Keeps `suggested_project_id` as the highest unambiguous candidate for existing consumers.

- [ ] **Step 1: unclassified API가 추천 3개와 최고 추천 ID를 반환해야 한다는 실패 API 테스트를 작성한다.**

```python
response = client.get(f"/api/v1/projects/{project['id']}/mail?status=unclassified&suggested=yes")
assert response.status_code == 200
mail = response.json()["data"][0]
assert mail["suggested_project_id"] == project["id"]
assert mail["suggestions"][0]["project_id"] == project["id"]
assert len(mail["suggestions"]) <= 3
```

- [ ] **Step 2: API가 아직 `suggestions`와 `suggested` 필터를 모르므로 실패하는지 확인한다.**

Run: `.venv/Scripts/python.exe -m pytest apps/backend/tests/test_mail_approval.py -q -k "suggestion" --tb=short`

Expected: `KeyError: 'suggestions'` 또는 422 validation failure.

- [ ] **Step 3: mail service에서 읽기 전용 프로젝트 맥락과 승인 이력을 수집하고 응답에 추천을 붙인다.**

```python
def _with_recommendations(self, message: MailMessage) -> MailMessage:
    suggestions = recommend_projects(message, list_project_contexts(self._db), self._approved_contexts())
    return dataclasses.replace(
        message,
        suggested_project_id=suggestions[0].project_id if suggestions else message.suggested_project_id,
        suggestions=suggestions,
    )
```

추천은 미분류 목록과 미분류 단건 상세에만 붙인다. 승인·제외 메일의 기존 DB 스냅샷에는 계산 결과를 저장하지 않는다. `suggested=yes|no`는 추천 부착 후, pagination 전에 적용한다.

- [ ] **Step 4: UI가 추천 프로젝트·관련도·근거를 표시하고 최고 후보를 승인 폼의 초기값으로 사용해야 한다는 실패 테스트를 작성한다.**

```tsx
await renderPage({ status: "unclassified" });
expect(screen.getByText("추천: 다온 정수장 · 높음")).toBeInTheDocument();
expect(screen.getByText("프로젝트명: 다온 정수장")).toBeInTheDocument();
expect(screen.getByRole("combobox", { name: "분류할 프로젝트" })).toHaveValue("project-daon");
```

- [ ] **Step 5: 필터 URL·목록 상태·승인 폼을 최소 변경으로 구현한다.**

```ts
const suggested = query.suggested === "yes" || query.suggested === "no" ? query.suggested : undefined;
const listResult = await fetchMailPage(projectId, status, page, suggested);
```

추천 필터는 관리자 미분류 탭에서만 렌더한다. 다른 상태·비관리자 요청은 필터를 노출하지 않으며 서버도 기존 권한 확인을 먼저 수행한다.

- [ ] **Step 6: API·UI 추천 테스트와 기존 메일 보안 테스트를 통과시킨다.**

Run: `.venv/Scripts/python.exe -m pytest apps/backend/tests/test_mail_approval.py apps/backend/tests/test_mail_recommendations.py -q --tb=short`

Run: `corepack pnpm --filter @lep/web exec vitest run src/widgets/mail/MailPage.test.tsx src/widgets/mail/MailPage.loading.test.tsx src/widgets/mail/MailApprovalForm.test.tsx`

Expected: PASS.

- [ ] **Step 7: 이 작업 파일만 커밋한다.**

```bash
git add apps/backend/src/lep/modules/mail/application/services.py apps/backend/src/lep/modules/mail/api/routes.py packages/api-client/src/domain.ts apps/web/src/shared/data/mail-review.ts 'apps/web/app/(app)/projects/[projectId]/mail/page.tsx' apps/web/src/widgets/mail/MailDetailSection.tsx apps/web/src/widgets/mail/MailApprovalForm.tsx apps/backend/tests/test_mail_approval.py apps/web/src/widgets/mail/MailPage.test.tsx apps/web/src/widgets/mail/MailPage.loading.test.tsx
git commit -m "feat: show project-context mail recommendations"
```

### Task 6: 전체 검증, 운영 배포 및 복구 기록

**Files:**
- Modify: `docs/work-packages/WP-MAIL-LOADING-PERFORMANCE.md`
- Modify: `docs/HANDOFF-2026-09-09-MAIL-PERFORMANCE.md`

**Interfaces:**
- Consumes: Task 1–5 code, existing Docker Compose health endpoints.
- Produces: 실제 테스트 결과, 배포 파일 목록, 서버 백업 위치와 health evidence.

- [ ] **Step 1: 백엔드·웹 전체 관련 검증을 실행한다.**

Run: `.venv/Scripts/python.exe -m pytest apps/backend/tests/test_mail_approval.py apps/backend/tests/test_mail_preview_cache.py apps/backend/tests/test_mail_drive_links.py apps/backend/tests/test_mail_recommendations.py -q --tb=short`

Run: `corepack pnpm --filter @lep/web exec vitest run src/widgets/mail app/layout.test.tsx --reporter=dot`

Run: `corepack pnpm --filter @lep/web typecheck`

Run: `corepack pnpm --filter @lep/web lint`

Run: `corepack pnpm --filter @lep/web build`

Expected: every command exits 0.

- [ ] **Step 2: 결과와 제한을 문서화한다.**

문서에 실행 명령·결과, migration 없음, 자동 승인 없음, 결정적 추천의 한계, 배포하지 않은 경우 그 사실을 정확히 적는다.

- [ ] **Step 3: 운영 서버의 변경 대상만 타임스탬프 백업한다.**

```bash
cd /opt/luminode/ERP
mkdir -p .deploy-backups/gailab-mail-YYYYMMDD-HHMM
cp -a <검증된-변경-대상> .deploy-backups/gailab-mail-YYYYMMDD-HHMM/
```

서버의 다른 미커밋 변경을 덮어쓰지 않는다. 전송할 각 파일의 차이와 백업 성공을 먼저 확인한다.

- [ ] **Step 4: 검증한 변경 파일만 전송하고 API·웹을 재빌드한다.**

```bash
cd /opt/luminode/ERP
docker compose -f infra/docker-compose.yml up -d --build api web
docker compose -f infra/docker-compose.yml ps
docker compose -f infra/docker-compose.yml exec -T api python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8000/health/ready', timeout=5).read().decode())"
```

Expected: api/web/db가 healthy이며 ready checks의 database, vault, uploads가 모두 `ok`.

- [ ] **Step 5: 검증·배포 문서만 커밋한다.**

```bash
git add docs/work-packages/WP-MAIL-LOADING-PERFORMANCE.md docs/HANDOFF-2026-09-09-MAIL-PERFORMANCE.md
git commit -m "docs: record GAILAB mail quality release"
```
