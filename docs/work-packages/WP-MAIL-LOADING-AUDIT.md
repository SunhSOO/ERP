# WP-MAIL-LOADING-AUDIT

Work Package ID: WP-MAIL-LOADING-AUDIT
Owned Module: mail adapter + mail page fetch orchestration
Goal: Diagnose slow mail loading with a synthetic POP3-only reproduction and isolate call-order costs.
In Scope:
- `HiworksMailAdapter` POP3 call path (`list_recent`, `get_message`)
- `MailReviewService` `_pending_messages`/`list_messages`/`counts` interactions (synthetic DB-free)
- page load fetch sequence in mail page
Out of Scope:
- Production endpoint changes
- UI behavior changes
- Real POP3/DB/LLM/service integrations
Dependencies:
- `apps/backend/src/lep/modules/mail/infrastructure/hiworks_pop3.py`
- `apps/backend/src/lep/modules/mail/application/services.py`
- `apps/backend/src/lep/modules/mail/public.py`
- `apps/backend/src/lep/modules/mail/api/routes.py`
- `apps/web/src/shared/data/mail-review.ts`
- `apps/web/app/(app)/projects/[projectId]/mail/page.tsx`
- `.mail-review-runs/diagnose-mail-loading.py` (new diagnostic harness)
API/Event contracts used:
- `GET /api/v1/projects/{project_id}/mail`
- `GET /api/v1/projects/{project_id}/mail/counts`
- `GET /api/v1/mail/{message_id}`
Tables owned: none (diagnostic-only)
Permissions affected: none
Migration needed: none
Tests required:
- Run `.mail-review-runs/diagnose-mail-loading.py` under mocked POP3 transport
- Keep as synthetic diagnostic evidence only
Risks/assumptions:
- POP3 server mailbox content is always read in full page-sized windows with `TOP` calls.
- Script assumes exactly 300 UIDLs are present and all have well-formed entries.
- Script monkeypatching for `require_project`/service internals means service-path checks are behavioral probes, not production integration tests.

## Executed diagnostic

- Command:
  - ``$env:PYTHONPATH='apps/backend/src'; .\.venv\Scripts\python.exe .\.mail-review-runs\diagnose-mail-loading.py``
- Date/locale context: synthetic, no network, no production credentials, no DB used.
- Script:
  - [`.mail-review-runs/diagnose-mail-loading.py`](.mail-review-runs/diagnose-mail-loading.py)

## Exact synthetic counts (fresh synthetic mailbox, `limit=300`, `uidl` count=300)

Adapter-only path:
- `connection_open=4`
- `stat=4`
- `uidl=4`
- `top=900`
- `retr=1`
- `rset=4`
- `quit=4`
- Loaded messages: page1=300 / page2=300 / page3=300 (`page3` emulates next-page repetition by re-list)
- `get_message` detail loaded from first UID of page1: `uid-300`
- Observed list_recent payload loads: 300 TOPs per page * 3 `list_recent()` calls = 900 TOP commands

Service-probe path (`MailReviewService` with synthetic overrides):
- `connection_open=3`
- `stat=3`
- `uidl=3`
- `top=900`
- `retr=0`
- `list_messages("unclassified", offset=0, limit=20)` returns 20 (total 300)
- `list_messages("unclassified", offset=20, limit=20)` returns 20 (total 300)
- `counts()` returns `{unclassified: 300, project: 0, unrelated: 0, all: 300}`

## Evidence (source lines)

- Adapter POP3 lifecycle and no result caching:
  - [hiworks adapter lifecycle and cleanup](apps/backend/src/lep/modules/mail/infrastructure/hiworks_pop3.py:303), [TOP-based preview fetch path](apps/backend/src/lep/modules/mail/infrastructure/hiworks_pop3.py:334), [full fetch retr path](apps/backend/src/lep/modules/mail/infrastructure/hiworks_pop3.py:366), [adapter cache is instance-level via `lru_cache`](apps/backend/src/lep/modules/mail/public.py:24)
- Service list/count/pending pipeline:
  - [unclassified path goes through `_pending_messages`](apps/backend/src/lep/modules/mail/application/services.py:173), [counts calls `_pending_messages`](apps/backend/src/lep/modules/mail/application/services.py:202), [`_pending_messages` calls adapter list once per service call](apps/backend/src/lep/modules/mail/application/services.py:700)
- API contract points:
  - [`list` endpoint](apps/backend/src/lep/modules/mail/api/routes.py:264), [`counts` endpoint](apps/backend/src/lep/modules/mail/api/routes.py:288)
- Front-end fetch order:
  - `Promise.all([list, counts, projects])` before detail fetch in mail page [front-end page load](apps/web/app/(app)/projects/[projectId]/mail/page.tsx:113)
  - default single-mail detail fetched after list/counts flow via `fetchMailById` [after list/selection resolution](apps/web/app/(app)/projects/[projectId]/mail/page.tsx:173)
  - classification note: list page uses preview and single fetch rehydrates full detail before render [same file lines 157–174](apps/web/app/(app)/projects/[projectId]/mail/page.tsx:157)

## Diagnosis of slowness source

- `list_recent()` is intentionally chatty by design: each call opens a new POP3 connection and calls `STAT`, `UIDL`, and `TOP` for up to `limit` messages.
- `list_messages`/`counts` paths repeatedly re-trigger that POP3 pass because there is no adapter-level list cache (`list_recent` always calls `_fetch`).
- The front-end currently waits for counts alongside list in one `Promise.all`, then still performs one more full fetch for selected message after list resolution (`fetchMailById`), which is expected by comments but adds another network roundtrip.
- There is no shared cache between calls for `mail` list content (`lru_cache` exists only for adapter creation at `get_mail_service`, not message data).

## Prioritized remedies (reviewed; diagnostic only, no implementation)

1. Share a short-lived raw mailbox preview snapshot at the adapter layer, scoped to the mailbox/account and connection configuration, with single-flight protection for concurrent list/count requests. A cache keyed separately by status/page will not share this expensive common collection. Reapply current DB classification and actor authorization per request; never cache approval or authorization decisions as raw-mail truth. Define freshness and account-change invalidation explicitly.
2. Render the list independently of counts and full detail using separate loading/error boundaries. Preserve single-message full-detail retrieval and all ID/project/classification checks before displaying full detail or enabling approval; the truncated list preview cannot replace these checks.
3. For longer-term incremental collection, compare a complete UIDL snapshot and reuse unchanged previews. A count plus latest UIDL alone cannot reliably detect every deletion or mailbox change.
4. Measure deployed request durations for list/count/detail and POP3 command totals without logging mail content or credentials, then verify cold/warm cache and concurrent-page behavior.

## Reviewer validation and limits

- Reviewer reran the diagnostic: exit 0; adapter 900 TOP + 1 RETR / 4 connections; service probe 900 TOP / 3 connections, returning 20 items for each of two pages.
- Service probe replaces `_pending_messages` and DB checks; real DB filtering/authorization correctness is not exercised by this diagnostic. Actual `_pending_messages` source was inspected separately.
- These counts demonstrate repeated collection, not deployed wall-clock latency. List/count requests are parallel in the UI, so their durations must not simply be summed.
- With 300 available messages and default collection limit, an admin unclassified page requires 300 TOP for list plus 300 TOP for counts; a selected unclassified message adds one RETR. A classified admin page still waits on the counts collection.
- Product source, API/events, permissions/audit, migrations and deployment were not changed in this inspection.
