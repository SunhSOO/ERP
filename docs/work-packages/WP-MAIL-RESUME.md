# WP-MAIL-RESUME

- Scope: mail API transport and related review UI.
- Added opt-in `id_encoding=base64url` for raw UIDLs containing path delimiters. The backend strictly validates canonical unpadded UTF-8 base64url and passes the restored raw ID to the existing service, preserving database identity and idempotency behavior.
- Added the shared frontend message-ID transport helper and propagated the marker through approval actions and the attachment proxy.
- Updated the review panel wording from AI analysis to classification reference, clarifying that sender/keyword suggestions require human confirmation.
- Fixed the mail approval test import ordering (Ruff I001).

Validation: final separated release candidate backend full suite 211 passed before the final test-only additions; final UIDL subset 9 passed, 52 deselected. Candidate frontend full suite 116 passed, including updated transport action assertions and two proxy marker regressions. Frontend typecheck, backend Ruff, mail routes mypy, API and web Docker builds passed. Product source/image equality verified.

Deployed mail-only release to the authorized company server on 2026-09-09. Existing additive migration created six new tables. API/web healthy; live/ready/login 200, unauthenticated mail detail 401, OpenAPI contract verified. No actual mail approvals performed. Rollback and source-reference attachment limitations are recorded in `../HANDOFF-2026-09-09-MAIL-APPROVAL.md`.
