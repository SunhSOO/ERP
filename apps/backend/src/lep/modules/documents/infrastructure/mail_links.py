"""Persistence for approved mail attachment references (ADR-021).

Everything here participates in the caller's transaction: no commit, no
outer rollback. ``register`` wraps its writes in a SAVEPOINT so a mid-batch
failure (a concurrent unique-constraint conflict) undoes only this call's
inserts, leaving the caller's own pending work intact.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as DbSession

from ....common.problems import ProblemError
from ..domain.entities import MailAttachmentLinkInput, MailAttachmentLinkRef
from .mail_link_models import MailAttachmentLinkRow


def _ensure_sqlite_outer_transaction(db: DbSession) -> None:
    """pysqlite only opens a real transaction lazily, on the first DML
    statement. If the caller's session has done nothing but reads so far,
    there is no physical transaction under our SAVEPOINT, so pysqlite's
    legacy driver treats the SAVEPOINT's ``RELEASE`` as a real commit — the
    caller's later ``rollback()`` then has nothing to undo. PostgreSQL is
    never affected: it begins a real transaction on first use."""

    connection = db.connection()
    if connection.dialect.name != "sqlite":
        return
    raw = connection.connection.driver_connection
    if raw is None:
        return
    if not raw.in_transaction:
        connection.exec_driver_sql("BEGIN")


def _mismatched(
    row: MailAttachmentLinkRow, project_id: str, item: MailAttachmentLinkInput
) -> bool:
    return (
        row.project_id != project_id
        or row.name != item.name
        or row.content_type != item.content_type
        or row.size_bytes != item.size_bytes
        or row.sha256 != item.sha256
        or row.category != item.category
    )


def register(
    db: DbSession,
    *,
    project_id: str,
    mailbox_key: str,
    message_id: str,
    actor_id: str,
    attachments: Sequence[MailAttachmentLinkInput],
) -> list[MailAttachmentLinkRef]:
    """Register a validated batch. Callers must already have de-duplicated
    ``attachments`` by ``part_index`` and validated every field."""

    part_indexes = [item.part_index for item in attachments]
    existing_by_part = {
        row.part_index: row
        for row in db.scalars(
            select(MailAttachmentLinkRow).where(
                MailAttachmentLinkRow.mailbox_key == mailbox_key,
                MailAttachmentLinkRow.message_id == message_id,
                MailAttachmentLinkRow.part_index.in_(part_indexes),
            )
        ).all()
    }

    refs: dict[int, MailAttachmentLinkRef] = {}
    to_insert: list[MailAttachmentLinkRow] = []
    for item in attachments:
        existing = existing_by_part.get(item.part_index)
        if existing is not None:
            if _mismatched(existing, project_id, item):
                raise ProblemError(
                    "STATE_CONFLICT",
                    "이미 다른 프로젝트 또는 메타데이터로 연결된 첨부입니다: "
                    f"part {item.part_index}",
                )
            refs[item.part_index] = MailAttachmentLinkRef(
                id=existing.id, part_index=item.part_index
            )
            continue

        row = MailAttachmentLinkRow(
            id=str(uuid.uuid4()),
            project_id=project_id,
            mailbox_key=mailbox_key,
            message_id=message_id,
            part_index=item.part_index,
            name=item.name,
            content_type=item.content_type,
            size_bytes=item.size_bytes,
            sha256=item.sha256,
            category=item.category,
            created_by=actor_id,
        )
        to_insert.append(row)
        refs[item.part_index] = MailAttachmentLinkRef(id=row.id, part_index=item.part_index)

    if to_insert:
        _ensure_sqlite_outer_transaction(db)
        try:
            with db.begin_nested():
                db.add_all(to_insert)
                db.flush()
        except IntegrityError as exc:
            raise ProblemError(
                "STATE_CONFLICT", "동시 등록 충돌로 첨부를 연결하지 못했습니다."
            ) from exc

    return [refs[item.part_index] for item in attachments]


def list_for_project(db: DbSession, project_id: str) -> list[MailAttachmentLinkRow]:
    """Read-only listing for the drive. Only ``documents``-owned rows; the mail
    module's own tables are never queried from here."""

    return list(
        db.scalars(
            select(MailAttachmentLinkRow)
            .where(MailAttachmentLinkRow.project_id == project_id)
            .order_by(MailAttachmentLinkRow.created_at)
        ).all()
    )
