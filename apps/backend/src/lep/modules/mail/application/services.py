"""Mail review workflow (ADR-021).

Automated classification is only ever a suggestion. A message's real state —
unclassified / project / unrelated — lives in ``mail_reviews`` and changes
only through :class:`MailReviewService`, which enforces permission, CAS
version, and idempotency before it touches the database or calls into
``documents`` to link attachments.

Everything here participates in the caller's request transaction (one
``DbSession`` per request via ``common.db.get_session``). No method commits;
a raised ``ProblemError`` propagates out to the route, and the session
dependency rolls the whole transaction back. That is what makes attachment
registration failures roll back the review row, its attachments, the audit
row, and the idempotency row together.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as DbSession

from ....bootstrap.trace import get_trace_id
from ....common.db import as_utc
from ....common.problems import ProblemError, not_found, state_conflict
from ...documents.public import (
    MailAttachmentLinkInput,
    MailAttachmentLinkRef,
    register_mail_attachments,
)
from ...iam.public import User
from ...knowledge.public import create_note_from
from ...projects.public import get_project_service, list_project_contexts, require_project
from ..application.recommendations import recommend_projects
from ..domain.entities import Classification, Confidence, MailAttachment, MailMessage
from ..domain.ports import MailPort
from ..infrastructure.models import (
    MailAuditRow,
    MailIdempotencyLinkRow,
    MailIdempotencyRow,
    MailReviewAttachmentRow,
    MailReviewRow,
)

#: 승인 요청에 쓸 수 있는 분류. WP 계약이 고정한 네 가지뿐이다.
ALLOWED_CATEGORIES = frozenset({"original", "report", "deliverable", "source"})

_MAX_IDEMPOTENCY_KEY_LENGTH = 200


def utc_now() -> datetime:
    return datetime.now(tz=UTC)


@dataclass(frozen=True, slots=True)
class AttachmentSelectionInput:
    part_index: int
    category: str


def payload_hash(
    *,
    action: str,
    mailbox_key: str,
    message_id: str,
    project_id: str | None,
    expected_version: int,
    attachments: list[tuple[int, str]],
) -> str:
    """SHA256 of a canonical payload. Identical requests hash identically;
    anything different — including selection order — does not, because the
    selections are sorted before hashing."""

    payload = {
        "action": action,
        "mailbox_key": mailbox_key,
        "message_id": message_id,
        "project_id": project_id,
        "expected_version": expected_version,
        "attachments": sorted(attachments),
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _ensure_sqlite_outer_transaction(db: DbSession) -> None:
    """pysqlite only opens a real transaction lazily, on the first DML
    statement. If the session has done nothing but reads so far, there is no
    physical transaction under the ``begin_nested()`` SAVEPOINT below, so
    pysqlite's legacy driver treats the SAVEPOINT's ``RELEASE`` as a real
    commit — a later ``rollback()`` on the outer session then has nothing to
    undo, and the "first insert" survives a request the caller believes it
    rolled back. PostgreSQL is never affected: it opens a real transaction on
    first use regardless. Mirrors ``documents.infrastructure.mail_links``."""

    connection = db.connection()
    if connection.dialect.name != "sqlite":
        return
    # ``driver_connection`` is pysqlite-specific and not on SQLAlchemy's
    # dialect-agnostic ``DBAPIConnection`` type; only ever present here
    # because the dialect check above already confirmed it is pysqlite.
    raw = getattr(connection.connection, "driver_connection", None)
    if raw is None:
        return
    if not raw.in_transaction:
        connection.exec_driver_sql("BEGIN")


class MailReviewService:
    """DB-backed classification workflow for one actor's request."""

    def __init__(self, db: DbSession, adapter: MailPort, actor: User) -> None:
        self._db = db
        self._adapter = adapter
        self._actor = actor

    # ── permission ───────────────────────────────────────────────────────

    def _is_active(self) -> bool:
        return self._actor.status.value == "active"

    def _is_reviewer(self) -> bool:
        """Active admin only. Reviewing the shared unclassified/unrelated
        queue — approving or dismissing — is not delegated to project
        creators (ADR-021, WP-PKD-MAIL-APPROVAL-20260909)."""

        return self._is_active() and self._actor.is_admin

    def _require_reviewer(self) -> None:
        if not self._is_reviewer():
            raise ProblemError("FORBIDDEN", "메일 검토는 관리자만 할 수 있습니다.")

    def _project_creator(self, project_id: str) -> str:
        return get_project_service(self._db).get_project(project_id).created_by

    def _can_view_project(self, project_id: str) -> bool:
        if not self._is_active():
            return False
        return self._actor.is_admin or self._project_creator(project_id) == self._actor.id

    def can_review(self) -> bool:
        return self._is_reviewer()

    # ── listing ──────────────────────────────────────────────────────────

    def list_messages(
        self, project_id: str, *, status: str, offset: int, limit: int, suggested: str | None = None
    ) -> tuple[list[MailMessage], int]:
        if status not in {"unclassified", "project", "unrelated", "all"}:
            raise ProblemError("VALIDATION_FAILED", "status 값이 올바르지 않습니다.")
        require_project(self._db, project_id)

        if status in {"unclassified", "unrelated"} and not self._is_reviewer():
            raise ProblemError("FORBIDDEN", "공용 검토함은 관리자만 볼 수 있습니다.")
        if status in {"project", "all"} and not self._can_view_project(project_id):
            raise ProblemError("FORBIDDEN", "이 프로젝트의 메일을 볼 권한이 없습니다.")

        if status == "project":
            return self._list_status(
                status="project", project_id=project_id, offset=offset, limit=limit
            )
        if status == "unrelated":
            return self._list_status(
                status="unrelated", project_id=None, offset=offset, limit=limit
            )
        if status == "unclassified":
            pending = self._pending_messages()
            with_recs = [self._with_recommendations(m) for m in pending]
            # Apply suggested filter before pagination (admin only, unclassified status only)
            if suggested is not None:
                if suggested == "yes":
                    with_recs = [m for m in with_recs if m.suggestions]
                elif suggested == "no":
                    with_recs = [m for m in with_recs if not m.suggestions]
            return self._paginate(with_recs, offset, limit)

        # status == "all": a non-reviewer (a project creator) never sees the
        # shared unclassified/unrelated queues, only their own project's
        # approved mail — this is not the reviewer's "everything" view.
        if not self._is_reviewer():
            return self._list_status(
                status="project", project_id=project_id, offset=offset, limit=limit
            )

        # Bound how much finalized mail each source contributes to the merge:
        # nothing beyond what this page could possibly need, so an old mailbox
        # with thousands of decided messages doesn't get loaded in full just
        # to render page 1.
        fetch_n = offset + limit
        pending = self._pending_messages()
        with_recs = [self._with_recommendations(m) for m in pending]
        unrelated, unrelated_total = self._list_status(
            status="unrelated", project_id=None, offset=0, limit=fetch_n
        )
        own_project, project_total = self._list_status(
            status="project", project_id=project_id, offset=0, limit=fetch_n
        )
        pool = with_recs[:fetch_n] + unrelated + own_project
        merged = sorted(pool, key=lambda m: (m.received_at, m.id), reverse=True)
        page, _ = self._paginate(merged, offset, limit)
        total = len(with_recs) + unrelated_total + project_total
        return page, total

    def counts(self, project_id: str) -> dict[str, int]:
        require_project(self._db, project_id)
        # One ``list_recent()`` call covers unclassified *and* the "all"
        # total below — Hiworks over POP3 has no server-side search, so a
        # naive per-status fetch would re-read the whole mailbox up to four
        # times for one counts request.
        if self._is_reviewer():
            unclassified = len(self._pending_messages())
            unrelated = self._count_status("unrelated", project_id=None)
        else:
            unclassified = 0
            unrelated = 0
        project = self._count_status("project", project_id=project_id) if self._can_view_project(
            project_id
        ) else 0
        total = unclassified + unrelated + project if self._is_reviewer() else project
        return {
            "unclassified": unclassified,
            "project": project,
            "unrelated": unrelated,
            "all": total,
        }

    def get(self, message_id: str) -> MailMessage:
        row = self._find_row(message_id)
        if row is None:
            if not self._is_reviewer():
                raise ProblemError("FORBIDDEN", "미분류 메일은 관리자만 볼 수 있습니다.")
            message = self._adapter.get_message(message_id)
            if message is None:
                raise not_found(f"메일을 찾을 수 없습니다: {message_id}")
            normalized = self._normalize_pending(message)
            return self._with_recommendations(normalized)
        if row.status == "unrelated" and not self._is_reviewer():
            raise ProblemError("FORBIDDEN", "제외 처리된 메일은 관리자만 볼 수 있습니다.")
        if row.status == "project":
            assert row.project_id is not None
            if not self._can_view_project(row.project_id):
                raise ProblemError("FORBIDDEN", "이 메일을 볼 권한이 없습니다.")
        return self._to_view(row, self._attachment_rows(row.id))

    # ── decisions ────────────────────────────────────────────────────────

    def approve(
        self,
        message_id: str,
        *,
        project_id: str,
        expected_version: int,
        attachments: list[AttachmentSelectionInput],
        idem_key: str,
    ) -> MailMessage:
        self._require_reviewer()
        require_project(self._db, project_id)
        selections = self._validate_selection(attachments)

        phash = payload_hash(
            action="approve",
            mailbox_key=self._adapter.mailbox_key,
            message_id=message_id,
            project_id=project_id,
            expected_version=expected_version,
            attachments=selections,
        )
        replay = self._check_idempotency(message_id, "approve", idem_key, phash)
        if replay is not None:
            return self._view_from_idempotency(replay)

        existing = self._find_row(message_id)
        if existing is not None:
            raise state_conflict("이미 분류된 메일입니다. 다른 프로젝트로 옮길 수 없습니다.")
        if expected_version != 0:
            raise state_conflict("버전이 일치하지 않습니다.")

        full = self._adapter.get_message(message_id)
        if full is None:
            raise not_found(f"메일을 찾을 수 없습니다: {message_id}")

        row = MailReviewRow(
            id=str(uuid.uuid4()),
            mailbox_key=self._adapter.mailbox_key,
            message_id=message_id,
            status="project",
            project_id=project_id,
            version=1,
            approved_by=self._actor.id,
            approved_at=utc_now(),
            sender_name=full.sender_name,
            sender_org=full.sender_org,
            received_at=full.received_at,
            subject=full.subject,
            body=full.body,
            intent=full.intent,
            confidence=full.confidence.value if full.confidence else None,
            milestone_code=full.milestone_code,
            suggested_project_id=full.suggested_project_id,
        )
        try:
            _ensure_sqlite_outer_transaction(self._db)
            with self._db.begin_nested():
                self._db.add(row)
                self._db.flush()
        except IntegrityError as exc:
            # A concurrent request for the exact same mail may have won this
            # race between our own precheck and this insert. If it used the
            # very same idempotency key, this is the same logical retry, not
            # a real conflict — report its result instead of a bare 409.
            raced_replay = self._check_idempotency(message_id, "approve", idem_key, phash)
            if raced_replay is not None:
                return self._view_from_idempotency(raced_replay)
            raise state_conflict("이미 처리된 메일입니다.") from exc

        attachment_rows = self._create_attachment_rows(
            row, full.attachments, selections, project_id
        )
        self._audit("approve", message_id, version=row.version, payload_hash=phash)
        linked = [r for r in attachment_rows if r.selected]
        self._save_idempotency(row, idem_key, phash, "approve", linked)
        return self._to_view(row, attachment_rows)

    def attachments_approve(
        self,
        message_id: str,
        *,
        expected_version: int,
        attachments: list[AttachmentSelectionInput],
        idem_key: str,
    ) -> MailMessage:
        """Link attachments to an already-approved mail, without changing its
        project (ADDITIONAL APPROVED SCOPE, WP-PKD-MAIL-APPROVAL-20260909)."""

        self._require_reviewer()
        selections = self._validate_selection(attachments)
        if not selections:
            raise ProblemError("VALIDATION_FAILED", "선택한 첨부가 없습니다.")

        phash = payload_hash(
            action="attachments_approve",
            mailbox_key=self._adapter.mailbox_key,
            message_id=message_id,
            project_id=None,
            expected_version=expected_version,
            attachments=selections,
        )
        replay = self._check_idempotency(message_id, "attachments_approve", idem_key, phash)
        if replay is not None:
            return self._view_from_idempotency(replay)

        row = self._find_row(message_id)
        if row is None:
            raise not_found(f"메일을 찾을 수 없습니다: {message_id}")
        if row.status != "project":
            raise state_conflict("프로젝트로 승인된 메일만 첨부를 추가할 수 있습니다.")
        if row.version != expected_version:
            raise state_conflict("버전이 일치하지 않습니다.")

        existing_rows = self._attachment_rows(row.id)
        existing_by_part = {r.part_index: r for r in existing_rows}
        for part_index, _category in selections:
            already = existing_by_part.get(part_index)
            if already is not None and already.selected:
                raise state_conflict(f"이미 연결된 첨부입니다: part {part_index}")

        full = self._adapter.get_message(message_id)
        if full is None:
            raise not_found(f"메일을 찾을 수 없습니다: {message_id}")
        known_by_part = {a.part_index: a for a in full.attachments}

        fetched: dict[int, tuple[str, str, bytes, str]] = {}
        for part_index, _category in selections:
            if part_index not in known_by_part:
                raise not_found(f"첨부를 찾을 수 없습니다: part {part_index}")
            content = self._adapter.fetch_attachment(message_id, part_index)
            if content is None:
                raise not_found(f"첨부를 찾을 수 없습니다: part {part_index}")
            filename, content_type, data = content
            fetched[part_index] = (filename, content_type, data, hashlib.sha256(data).hexdigest())

        assert row.project_id is not None
        refs = register_mail_attachments(
            self._db,
            project_id=row.project_id,
            mailbox_key=row.mailbox_key,
            message_id=row.message_id,
            actor_id=self._actor.id,
            attachments=[
                MailAttachmentLinkInput(
                    part_index=pi,
                    name=fetched[pi][0],
                    content_type=fetched[pi][1],
                    size_bytes=len(fetched[pi][2]),
                    sha256=fetched[pi][3],
                    category=category,
                )
                for pi, category in selections
            ],
        )
        ref_by_part = self._validate_link_refs(refs, selections)

        for part_index, category in selections:
            filename, content_type, data, sha = fetched[part_index]
            target = existing_by_part.get(part_index)
            if target is None:
                target = MailReviewAttachmentRow(
                    id=str(uuid.uuid4()), review_id=row.id, part_index=part_index,
                    filename=filename, content_type=content_type, size_bytes=len(data),
                )
                self._db.add(target)
                existing_by_part[part_index] = target
            target.selected = True
            target.category = category
            target.filename = filename
            target.content_type = content_type
            target.size_bytes = len(data)
            target.sha256 = sha
            target.linked_file_id = ref_by_part[part_index]

        result = self._db.execute(
            update(MailReviewRow)
            .where(MailReviewRow.id == row.id, MailReviewRow.version == expected_version)
            .values(version=MailReviewRow.version + 1)
        )
        if result.rowcount != 1:
            raise state_conflict("버전이 일치하지 않습니다.")
        self._db.flush()
        self._db.refresh(row)

        # 이 커맨드가 링크한 것만이 아니라, 이 시점에 실제로 연결된 첨부
        # 전체를 스냅샷한다 — 재현 응답이 "이 커맨드가 끝났을 때의 전체
        # 상태"를 보여줘야 하기 때문이다.
        linked_now = [r for r in self._attachment_rows(row.id) if r.selected]
        self._audit("attachments_approve", message_id, version=row.version, payload_hash=phash)
        self._save_idempotency(row, idem_key, phash, "attachments_approve", linked_now)
        return self._to_view(row, self._attachment_rows(row.id))

    def dismiss(self, message_id: str, *, expected_version: int, idem_key: str) -> MailMessage:
        self._require_reviewer()

        phash = payload_hash(
            action="dismiss",
            mailbox_key=self._adapter.mailbox_key,
            message_id=message_id,
            project_id=None,
            expected_version=expected_version,
            attachments=[],
        )
        replay = self._check_idempotency(message_id, "dismiss", idem_key, phash)
        if replay is not None:
            return self._view_from_idempotency(replay)

        existing = self._find_row(message_id)
        if existing is not None:
            raise state_conflict("이미 처리된 메일입니다.")
        if expected_version != 0:
            raise state_conflict("버전이 일치하지 않습니다.")

        full = self._adapter.get_message(message_id)
        if full is None:
            raise not_found(f"메일을 찾을 수 없습니다: {message_id}")

        row = MailReviewRow(
            id=str(uuid.uuid4()),
            mailbox_key=self._adapter.mailbox_key,
            message_id=message_id,
            status="unrelated",
            project_id=None,
            version=1,
            approved_by=self._actor.id,
            approved_at=utc_now(),
            sender_name=full.sender_name,
            sender_org=full.sender_org,
            received_at=full.received_at,
            subject=full.subject,
            body=full.body,
            intent=full.intent,
            confidence=full.confidence.value if full.confidence else None,
            milestone_code=full.milestone_code,
            suggested_project_id=full.suggested_project_id,
        )
        try:
            _ensure_sqlite_outer_transaction(self._db)
            with self._db.begin_nested():
                self._db.add(row)
                self._db.flush()
        except IntegrityError as exc:
            # A concurrent request for the exact same mail may have won this
            # race between our own precheck and this insert. If it used the
            # very same idempotency key, this is the same logical retry, not
            # a real conflict — report its result instead of a bare 409.
            raced_replay = self._check_idempotency(message_id, "dismiss", idem_key, phash)
            if raced_replay is not None:
                return self._view_from_idempotency(raced_replay)
            raise state_conflict("이미 처리된 메일입니다.") from exc

        # Dismissed mail still keeps its attachment metadata (name/type/size)
        # for the record — none of it is selected, hashed, or registered with
        # documents. There is no drive-worthy file for an excluded message.
        attachment_rows = self._snapshot_attachment_rows(row, full.attachments)

        self._audit("dismiss", message_id, version=row.version, payload_hash=phash)
        self._save_idempotency(row, idem_key, phash, "dismiss", [])
        return self._to_view(row, attachment_rows)

    # ── attachments ──────────────────────────────────────────────────────

    def fetch_attachment(
        self, message_id: str, part_index: int, *, linked_file_id: str | None = None
    ) -> tuple[str, str, bytes]:
        """Download one attachment.

        ``linked_file_id`` is optional and, when present, must equal exactly
        the linked reference ID this *current* mailbox_key+UIDL+part review
        attachment stored. It exists so a drive link minted for one mailbox
        cannot silently resolve against another after the configured
        mailbox/account is switched but a UIDL+part number is reused — the
        query alone never bypasses the actor/hash checks below it (WP-PKD-
        MAIL-APPROVAL-20260909)."""

        row = self._find_row(message_id)

        if row is None:
            if not self._is_reviewer():
                raise ProblemError("FORBIDDEN", "미분류 첨부는 관리자만 볼 수 있습니다.")
            if linked_file_id is not None:
                raise not_found(f"첨부를 찾을 수 없습니다: {message_id}/{part_index}")
            content = self._adapter.fetch_attachment(message_id, part_index)
            if content is None:
                raise not_found(f"첨부를 찾을 수 없습니다: {message_id}/{part_index}")
            self._audit("download", message_id, version=0, payload_hash=None, part_index=part_index)
            return content

        if row.status == "unrelated":
            raise not_found(f"첨부를 찾을 수 없습니다: {message_id}/{part_index}")

        assert row.project_id is not None
        can_view = self._can_view_project(row.project_id)
        if not can_view:
            raise ProblemError("FORBIDDEN", "이 첨부를 볼 권한이 없습니다.")

        attachment_row = self._db.scalar(
            select(MailReviewAttachmentRow).where(
                MailReviewAttachmentRow.review_id == row.id,
                MailReviewAttachmentRow.part_index == part_index,
            )
        )

        if attachment_row is None or not attachment_row.selected:
            if linked_file_id is not None:
                raise not_found(f"첨부를 찾을 수 없습니다: {message_id}/{part_index}")
            if not self._actor.is_admin:
                raise not_found(f"첨부를 찾을 수 없습니다: {message_id}/{part_index}")
            # Admin preview of a not-yet-linked attachment: re-read from source.
            content = self._adapter.fetch_attachment(message_id, part_index)
            if content is None:
                raise not_found(f"첨부를 찾을 수 없습니다: {message_id}/{part_index}")
            self._audit(
                "download", message_id,
                version=row.version, payload_hash=None, part_index=part_index,
            )
            return content

        if linked_file_id is not None and linked_file_id != attachment_row.linked_file_id:
            # Never fetch the source payload for a mismatched linked_file_id —
            # this is exactly the stale-drive-link-after-account-switch case.
            raise not_found(f"첨부를 찾을 수 없습니다: {message_id}/{part_index}")

        content = self._adapter.fetch_attachment(message_id, part_index)
        if content is None:
            raise not_found("원본 첨부를 더 이상 찾을 수 없습니다.")
        filename, content_type, data = content
        sha = hashlib.sha256(data).hexdigest()
        if sha != attachment_row.sha256 or len(data) != attachment_row.size_bytes:
            raise state_conflict("원본 첨부 내용이 승인 시점과 다릅니다.")
        self._audit(
            "download", message_id, version=row.version, payload_hash=None, part_index=part_index
        )
        return (attachment_row.filename, attachment_row.content_type, data)

    # ── promote to note ──────────────────────────────────────────────────

    def promote_to_note(self, message_id: str) -> str:
        """Write the mail into the project's knowledge vault, exactly once.

        The vault write is an external call with no shared transaction with
        this database — two concurrent requests could otherwise both pass the
        ``note_id is None`` read and both write a note. To close that race,
        the loser must be turned away by an atomic, CAS-guarded UPDATE
        *before* ``create_note_from`` ever runs, not after. The unavoidable
        gap that remains: if ``create_note_from`` itself raises after this
        reservation succeeds, the review is left permanently reserved with no
        note actually written (there is no distributed transaction across the
        database and the vault to undo the reservation) — a known limitation
        of the two-system design, not something this method can fully close.
        """

        row = self._find_row(message_id)
        if row is None or row.status != "project":
            raise state_conflict("프로젝트로 승인된 메일만 지식화할 수 있습니다.")
        assert row.project_id is not None
        if not self._can_view_project(row.project_id):
            raise ProblemError("FORBIDDEN", "이 메일을 지식화할 권한이 없습니다.")
        if row.note_id is not None:
            raise state_conflict("이미 지식화된 메일입니다.")

        reservation = f"__promoting__:{uuid.uuid4()}"
        result = self._db.execute(
            update(MailReviewRow)
            .where(
                MailReviewRow.id == row.id,
                MailReviewRow.version == row.version,
                MailReviewRow.note_id.is_(None),
            )
            .values(note_id=reservation, version=MailReviewRow.version + 1)
        )
        if result.rowcount != 1:
            raise state_conflict("이미 지식화된 메일입니다.")
        self._db.flush()

        project = require_project(self._db, row.project_id)
        title = row.subject or "제목 없는 메일"
        stem = create_note_from(
            project.code,
            title=title,
            body=(
                f"# {title}\n\n"
                f"출처: 메일 {row.message_id}\n"
                f"보낸 사람: {row.sender_name} ({row.sender_org})\n"
                f"받은 시각: {as_utc(row.received_at).isoformat() if row.received_at else ''}\n\n"
                f"{row.body}\n"
            ),
            folder="inbox",
        )
        self._db.execute(
            update(MailReviewRow).where(MailReviewRow.id == row.id).values(note_id=stem)
        )
        self._db.flush()
        self._db.refresh(row)
        self._audit("promote_to_note", message_id, version=row.version, payload_hash=None)
        return stem

    # ── internals: queries ───────────────────────────────────────────────

    def _find_row(self, message_id: str) -> MailReviewRow | None:
        return self._db.scalar(
            select(MailReviewRow).where(
                MailReviewRow.mailbox_key == self._adapter.mailbox_key,
                MailReviewRow.message_id == message_id,
            )
        )

    def _attachment_rows(self, review_id: str) -> list[MailReviewAttachmentRow]:
        return list(
            self._db.scalars(
                select(MailReviewAttachmentRow)
                .where(MailReviewAttachmentRow.review_id == review_id)
                .order_by(MailReviewAttachmentRow.part_index)
            ).all()
        )

    def _attachment_rows_for(
        self, review_ids: list[str]
    ) -> dict[str, list[MailReviewAttachmentRow]]:
        """One query for every row on a page, instead of one per row (N+1)."""

        by_review: dict[str, list[MailReviewAttachmentRow]] = {rid: [] for rid in review_ids}
        for attachment_row in self._db.scalars(
            select(MailReviewAttachmentRow)
            .where(MailReviewAttachmentRow.review_id.in_(review_ids))
            .order_by(MailReviewAttachmentRow.review_id, MailReviewAttachmentRow.part_index)
        ).all():
            by_review.setdefault(attachment_row.review_id, []).append(attachment_row)
        return by_review

    @staticmethod
    def _normalize_pending(message: MailMessage) -> MailMessage:
        """A message with no review row is unclassified, full stop — no
        matter what a legacy adapter overlay (``handled``/``note_id`` kept in
        process memory for backward compatibility) says. Approval identity
        lives only in the database; an overlay is not a substitute for it."""

        return dataclasses.replace(
            message,
            classification=Classification.UNCLASSIFIED,
            project_id=None,
            note_id=None,
            handled=False,
            version=0,
            approved_by=None,
            approved_at=None,
        )

    def _pending_messages(self) -> list[MailMessage]:
        decided_ids = set(
            self._db.scalars(
                select(MailReviewRow.message_id).where(
                    MailReviewRow.mailbox_key == self._adapter.mailbox_key
                )
            ).all()
        )
        raw = self._adapter.list_recent()
        pending = [self._normalize_pending(m) for m in raw if m.id not in decided_ids]
        return sorted(pending, key=lambda m: (m.received_at, m.id), reverse=True)

    def _list_status(
        self, *, status: str, project_id: str | None, offset: int, limit: int | None
    ) -> tuple[list[MailMessage], int]:
        base = select(MailReviewRow.id).where(
            MailReviewRow.mailbox_key == self._adapter.mailbox_key,
            MailReviewRow.status == status,
        )
        if project_id is not None:
            base = base.where(MailReviewRow.project_id == project_id)

        total = self._db.scalar(select(func.count()).select_from(base.subquery())) or 0

        id_stmt = base.order_by(MailReviewRow.received_at.desc(), MailReviewRow.id.desc())
        if limit is not None:
            id_stmt = id_stmt.offset(offset).limit(limit)
        page_ids = list(self._db.scalars(id_stmt).all())
        if not page_ids:
            return [], total

        rows_by_id = {
            row.id: row
            for row in self._db.scalars(
                select(MailReviewRow).where(MailReviewRow.id.in_(page_ids))
            ).all()
        }
        attachments_by_review = self._attachment_rows_for(page_ids)
        views = [
            self._to_view(rows_by_id[rid], attachments_by_review.get(rid, [])) for rid in page_ids
        ]
        return views, total

    def _count_status(self, status: str, *, project_id: str | None) -> int:
        stmt = select(func.count()).select_from(MailReviewRow).where(
            MailReviewRow.mailbox_key == self._adapter.mailbox_key,
            MailReviewRow.status == status,
        )
        if project_id is not None:
            stmt = stmt.where(MailReviewRow.project_id == project_id)
        return self._db.scalar(stmt) or 0

    @staticmethod
    def _paginate(
        items: list[MailMessage], offset: int, limit: int
    ) -> tuple[list[MailMessage], int]:
        total = len(items)
        return items[offset : offset + limit], total

    def _to_view(
        self, row: MailReviewRow, attachment_rows: list[MailReviewAttachmentRow]
    ) -> MailMessage:
        return MailMessage(
            id=row.message_id,
            sender_name=row.sender_name,
            sender_org=row.sender_org,
            received_at=as_utc(row.received_at) if row.received_at else utc_now(),
            subject=row.subject,
            body=row.body,
            classification=Classification(row.status),
            project_id=row.project_id,
            intent=row.intent,
            confidence=Confidence(row.confidence) if row.confidence else None,
            milestone_code=row.milestone_code,
            note_id=row.note_id,
            handled=row.status != "unclassified",
            attachments=tuple(
                MailAttachment(
                    filename=a.filename, content_type=a.content_type, size_bytes=a.size_bytes,
                    part_index=a.part_index, linked_file_id=a.linked_file_id,
                )
                for a in attachment_rows
            ),
            suggested_project_id=row.suggested_project_id,
            version=row.version,
            approved_by=row.approved_by,
            approved_at=as_utc(row.approved_at) if row.approved_at else None,
        )

    # ── internals: attachment persistence ───────────────────────────────

    def _validate_selection(
        self, attachments: list[AttachmentSelectionInput]
    ) -> list[tuple[int, str]]:
        seen: set[int] = set()
        normalized: list[tuple[int, str]] = []
        for item in attachments:
            if item.part_index < 0:
                raise ProblemError("VALIDATION_FAILED", "part_index는 0 이상이어야 합니다.")
            if item.part_index in seen:
                raise ProblemError(
                    "VALIDATION_FAILED", f"중복된 첨부 선택입니다: part {item.part_index}"
                )
            seen.add(item.part_index)
            if item.category not in ALLOWED_CATEGORIES:
                raise ProblemError(
                    "VALIDATION_FAILED", f"허용되지 않는 분류입니다: {item.category}"
                )
            normalized.append((item.part_index, item.category))
        return normalized

    @staticmethod
    def _validate_link_refs(
        refs: list[MailAttachmentLinkRef], selections: list[tuple[int, str]]
    ) -> dict[int, str]:
        """``documents.public.register_mail_attachments`` is another module's
        contract — never trust its shape blindly. Exactly one ref per
        requested part, no duplicate parts, and every id a real, non-empty
        UUID; anything else means the two modules' state has already
        diverged, and the whole approval must fail loudly (never silently
        record ``selected=true`` with a missing link)."""

        requested_parts = {part_index for part_index, _ in selections}
        if len(refs) != len(selections):
            raise ProblemError(
                "INTEGRATION_ERROR", "문서 연동 결과 개수가 요청한 첨부 수와 다릅니다."
            )
        seen_parts: set[int] = set()
        ref_by_part: dict[int, str] = {}
        for ref in refs:
            if ref.part_index in seen_parts:
                raise ProblemError(
                    "INTEGRATION_ERROR",
                    f"문서 연동 결과에 중복된 part가 있습니다: {ref.part_index}",
                )
            seen_parts.add(ref.part_index)
            if not ref.id or not ref.id.strip():
                raise ProblemError(
                    "INTEGRATION_ERROR",
                    f"문서 연동 결과의 id가 비어 있습니다: part {ref.part_index}",
                )
            try:
                uuid.UUID(ref.id)
            except ValueError as exc:
                raise ProblemError(
                    "INTEGRATION_ERROR",
                    f"문서 연동 결과의 id 형식이 올바르지 않습니다: part {ref.part_index}",
                ) from exc
            ref_by_part[ref.part_index] = ref.id
        if seen_parts != requested_parts:
            raise ProblemError(
                "INTEGRATION_ERROR", "문서 연동 결과가 요청한 첨부 집합과 다릅니다."
            )
        return ref_by_part

    def _snapshot_attachment_rows(
        self, row: MailReviewRow, known_attachments: tuple[MailAttachment, ...]
    ) -> list[MailReviewAttachmentRow]:
        """Record every attachment's metadata at decision time, unselected —
        used for ``dismiss``, where nothing is fetched, hashed, or registered
        with documents, but the message's attachment list should still be
        visible in the audit-quality record of what the message contained."""

        rows = [
            MailReviewAttachmentRow(
                id=str(uuid.uuid4()), review_id=row.id, part_index=att.part_index,
                filename=att.filename, content_type=att.content_type, size_bytes=att.size_bytes,
            )
            for att in known_attachments
        ]
        self._db.add_all(rows)
        self._db.flush()
        return rows

    def _create_attachment_rows(
        self,
        row: MailReviewRow,
        known_attachments: tuple[MailAttachment, ...],
        selections: list[tuple[int, str]],
        project_id: str,
    ) -> list[MailReviewAttachmentRow]:
        known_by_part = {a.part_index: a for a in known_attachments}
        rows: dict[int, MailReviewAttachmentRow] = {
            att.part_index: MailReviewAttachmentRow(
                id=str(uuid.uuid4()), review_id=row.id, part_index=att.part_index,
                filename=att.filename, content_type=att.content_type, size_bytes=att.size_bytes,
            )
            for att in known_attachments
        }

        fetched: dict[int, tuple[str, str, bytes, str]] = {}
        for part_index, _category in selections:
            if part_index not in known_by_part:
                raise not_found(f"첨부를 찾을 수 없습니다: part {part_index}")
            content = self._adapter.fetch_attachment(row.message_id, part_index)
            if content is None:
                raise not_found(f"첨부를 찾을 수 없습니다: part {part_index}")
            filename, content_type, data = content
            fetched[part_index] = (filename, content_type, data, hashlib.sha256(data).hexdigest())

        if selections:
            refs = register_mail_attachments(
                self._db,
                project_id=project_id,
                mailbox_key=row.mailbox_key,
                message_id=row.message_id,
                actor_id=self._actor.id,
                attachments=[
                    MailAttachmentLinkInput(
                        part_index=pi, name=fetched[pi][0], content_type=fetched[pi][1],
                        size_bytes=len(fetched[pi][2]), sha256=fetched[pi][3], category=category,
                    )
                    for pi, category in selections
                ],
            )
            ref_by_part = self._validate_link_refs(refs, selections)
            for part_index, category in selections:
                target = rows[part_index]
                filename, content_type, data, sha = fetched[part_index]
                target.selected = True
                target.category = category
                target.filename = filename
                target.content_type = content_type
                target.size_bytes = len(data)
                target.sha256 = sha
                target.linked_file_id = ref_by_part[part_index]

        all_rows = list(rows.values())
        self._db.add_all(all_rows)
        self._db.flush()
        return all_rows

    # ── internals: idempotency ──────────────────────────────────────────

    def _check_idempotency(
        self, message_id: str, action: str, key: str, phash: str
    ) -> MailIdempotencyRow | None:
        if not key or not key.strip() or len(key) > _MAX_IDEMPOTENCY_KEY_LENGTH:
            raise ProblemError("VALIDATION_FAILED", "Idempotency-Key가 필요합니다.")
        existing = self._db.scalar(
            select(MailIdempotencyRow).where(
                MailIdempotencyRow.mailbox_key == self._adapter.mailbox_key,
                MailIdempotencyRow.idempotency_key == key,
            )
        )
        if existing is None:
            return None
        if (
            existing.actor_id != self._actor.id
            or existing.message_id != message_id
            or existing.action != action
        ):
            raise state_conflict("Idempotency-Key가 다른 요청과 충돌합니다.")
        if existing.payload_hash != phash:
            raise state_conflict("Idempotency-Key가 다른 요청 내용과 충돌합니다.")
        return existing

    def _save_idempotency(
        self,
        row: MailReviewRow,
        key: str,
        phash: str,
        action: str,
        linked_rows: list[MailReviewAttachmentRow],
    ) -> None:
        idem = MailIdempotencyRow(
            id=str(uuid.uuid4()), mailbox_key=row.mailbox_key, message_id=row.message_id,
            idempotency_key=key, actor_id=self._actor.id, action=action,
            payload_hash=phash, review_id=row.id, result_version=row.version,
            result_note_id=row.note_id,
        )
        try:
            _ensure_sqlite_outer_transaction(self._db)
            with self._db.begin_nested():
                self._db.add(idem)
                self._db.flush()
        except IntegrityError as exc:
            # A concurrent request reused this same key for a different mail
            # (or a different action) — a genuine conflict, not a replay of
            # this command. Never let the raw unique-constraint failure surface
            # as a 500; the whole approval still rolls back with this raise.
            raise state_conflict("Idempotency-Key가 다른 요청과 충돌합니다.") from exc
        for attachment_row in linked_rows:
            self._db.add(
                MailIdempotencyLinkRow(
                    id=str(uuid.uuid4()), idempotency_id=idem.id,
                    review_attachment_id=attachment_row.id,
                )
            )
        self._db.flush()

    def _view_from_idempotency(self, existing: MailIdempotencyRow) -> MailMessage:
        """Reconstruct exactly what this command reported when it first ran:
        the version and ``note_id`` right after it completed, and the entire
        attachment link set as of that moment — not whatever the review has
        grown into since (a later command's extra links, or a later
        promotion's ``note_id``)."""

        row = self._db.get(MailReviewRow, existing.review_id)
        assert row is not None
        linked_ids = {
            link.review_attachment_id
            for link in self._db.scalars(
                select(MailIdempotencyLinkRow).where(
                    MailIdempotencyLinkRow.idempotency_id == existing.id
                )
            ).all()
        }
        all_rows = self._attachment_rows(row.id)
        attachments = tuple(
            MailAttachment(
                filename=a.filename, content_type=a.content_type, size_bytes=a.size_bytes,
                part_index=a.part_index,
                linked_file_id=a.linked_file_id if a.id in linked_ids else None,
            )
            for a in all_rows
        )
        return MailMessage(
            id=row.message_id, sender_name=row.sender_name, sender_org=row.sender_org,
            received_at=as_utc(row.received_at) if row.received_at else utc_now(),
            subject=row.subject, body=row.body, classification=Classification(row.status),
            project_id=row.project_id, intent=row.intent,
            confidence=Confidence(row.confidence) if row.confidence else None,
            milestone_code=row.milestone_code, note_id=existing.result_note_id,
            handled=row.status != "unclassified", attachments=attachments,
            suggested_project_id=row.suggested_project_id, version=existing.result_version,
            approved_by=row.approved_by,
            approved_at=as_utc(row.approved_at) if row.approved_at else None,
        )

    # ── internals: recommendations ────────────────────────────────────────

    def _approved_contexts(self) -> tuple[tuple[str, str | None, str | None], ...]:
        """Collect project context from approved mails for recommendation scoring."""
        rows = self._db.scalars(
            select(MailReviewRow).where(
                MailReviewRow.mailbox_key == self._adapter.mailbox_key,
                MailReviewRow.status == "project",
            )
        ).all()
        # project_id는 nullable 컬럼이다. status가 project인 행에는 항상 있어야
        # 하지만, 없는 행을 None인 채로 흘려보내면 점수 계산이 그것을 프로젝트
        # 식별자로 받는다. 타입으로 거짓말하지 않고 여기서 거른다.
        return tuple(
            (row.project_id, row.intent, row.milestone_code)
            for row in rows
            if row.project_id is not None
        )

    def _with_recommendations(self, message: MailMessage) -> MailMessage:
        """Attach project context recommendations to an unclassified message."""
        if message.classification != Classification.UNCLASSIFIED:
            return message

        projects = list_project_contexts(self._db)
        approved_contexts = self._approved_contexts()
        suggestions = recommend_projects(message, projects, approved_contexts)

        return dataclasses.replace(
            message,
            suggested_project_id=(
                suggestions[0].project_id if suggestions else message.suggested_project_id
            ),
            suggestions=suggestions,
        )

    # ── internals: audit ─────────────────────────────────────────────────

    def _audit(
        self,
        action: str,
        message_id: str,
        *,
        version: int | None,
        payload_hash: str | None,
        part_index: int | None = None,
    ) -> None:
        self._db.add(
            MailAuditRow(
                id=str(uuid.uuid4()), actor_id=self._actor.id, action=action,
                mailbox_key=self._adapter.mailbox_key, message_id=message_id,
                part_index=part_index, version=version, payload_hash=payload_hash,
                trace_id=get_trace_id(),
            )
        )
        self._db.flush()
