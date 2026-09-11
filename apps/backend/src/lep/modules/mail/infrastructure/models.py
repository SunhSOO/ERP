"""SQLAlchemy tables owned by the mail module (ADR-021).

``mail_reviews`` is the sole source of truth for classification state. A row
only exists once a message has been decided (approved to a project or
dismissed as unrelated); undecided mail has no row and is reported
unclassified straight from the adapter. The row also carries a snapshot of
the message content taken at decision time, so the approved/dismissed lists
keep working even after the source mail scrolls out of the adapter's reading
window or is deleted.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from ....common.db import Base


def utc_now() -> datetime:
    return datetime.now(tz=UTC)


class MailReviewRow(Base):
    __tablename__ = "mail_reviews"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    mailbox_key: Mapped[str] = mapped_column(String(64), nullable=False)
    message_id: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="unclassified")
    project_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="RESTRICT"), nullable=True
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    approved_by: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # ── 결정 시점 스냅샷. 원본이 사라져도 승인/제외 목록은 그대로 읽힌다.
    # RFC 2047 디코딩 결과나 실제 조직명은 255자를 넘을 수 있어 Text로 둔다 —
    # SQLite는 VARCHAR 길이를 강제하지 않아 테스트에서 조용히 통과하고
    # PostgreSQL에서만 터지는 문제를 막는다.
    sender_name: Mapped[str] = mapped_column(Text, nullable=False, default="")
    sender_org: Mapped[str] = mapped_column(Text, nullable=False, default="")
    received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    subject: Mapped[str] = mapped_column(Text, nullable=False, default="")
    body: Mapped[str] = mapped_column(Text, nullable=False, default="")
    intent: Mapped[str | None] = mapped_column(String(100), nullable=True)
    confidence: Mapped[str | None] = mapped_column(String(10), nullable=True)
    milestone_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    suggested_project_id: Mapped[str | None] = mapped_column(String(36), nullable=True)

    note_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )

    __table_args__ = (
        UniqueConstraint("mailbox_key", "message_id", name="uq_mail_review_mailbox_message"),
        CheckConstraint(
            "status in ('unclassified','project','unrelated')", name="ck_mail_review_status"
        ),
        CheckConstraint("version >= 0", name="ck_mail_review_version_nonneg"),
        # 상태와 그 상태가 요구하는 필드가 늘 함께 간다: 미분류는 확정 필드가
        # 전부 비어 있고, project/unrelated(둘 다 "결정됨")는 approved_by/
        # approved_at이 반드시 있고, project만 project_id도 있다.
        CheckConstraint(
            "(status = 'unclassified' AND project_id IS NULL "
            " AND approved_by IS NULL AND approved_at IS NULL)"
            " OR (status = 'unrelated' AND project_id IS NULL "
            " AND approved_by IS NOT NULL AND approved_at IS NOT NULL)"
            " OR (status = 'project' AND project_id IS NOT NULL "
            " AND approved_by IS NOT NULL AND approved_at IS NOT NULL)",
            name="ck_mail_review_status_fields_coherent",
        ),
        Index("ix_mail_review_project_id", "project_id"),
        Index("ix_mail_review_mailbox_status", "mailbox_key", "status"),
        Index("ix_mail_review_approved_by", "approved_by"),
    )


class MailReviewAttachmentRow(Base):
    """Every attachment known at decision time, selected or not.

    Only ``selected`` rows carry a confirmed ``sha256``/``linked_file_id`` —
    those are the only ones whose bytes were actually fetched and registered.
    """

    __tablename__ = "mail_review_attachments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    #: RESTRICT, uniform with every other approval-history FK here: a
    #: review's attachment snapshot is part of the decision record, not
    #: disposable detail that should vanish silently if a review row were
    #: ever deleted (nothing does that today, but the constraint should not
    #: depend on that staying true).
    review_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("mail_reviews.id", ondelete="RESTRICT"), nullable=False
    )
    part_index: Mapped[int] = mapped_column(Integer, nullable=False)
    #: RFC 2047 디코딩 결과라 255자를 넘을 수 있다 (documents 쪽 링크 테이블과
    #: 달리 여기서는 문서 계약이 아니라 스냅샷일 뿐이라 자유롭게 Text로 둔다).
    filename: Mapped[str] = mapped_column(Text, nullable=False)
    content_type: Mapped[str] = mapped_column(String(255), nullable=False)
    #: PostgreSQL의 32비트 INTEGER는 2GB를 넘는 첨부에서 조용히 넘칠 수 있다 —
    #: documents의 링크 테이블과 같은 BigInteger로 맞춘다.
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    selected: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    category: Mapped[str | None] = mapped_column(String(20), nullable=True)
    linked_file_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )

    __table_args__ = (
        UniqueConstraint("review_id", "part_index", name="uq_mail_review_attachment_part"),
        CheckConstraint("part_index >= 0", name="ck_mail_review_attachment_part_nonneg"),
        CheckConstraint("size_bytes >= 0", name="ck_mail_review_attachment_size_nonneg"),
        # 실제로 fetch해서 documents에 등록한 행만 selected다 — sha256/category/
        # linked_file_id는 그 등록이 성공했을 때만 채워진다. linked_file_id
        # 없이 selected=true인 행은 documents 응답을 검증 없이 신뢰했다는
        # 뜻이라 여기서 막는다.
        CheckConstraint(
            "selected = false OR "
            "(sha256 IS NOT NULL AND category IS NOT NULL AND linked_file_id IS NOT NULL)",
            name="ck_mail_review_attachment_selected_requires_metadata",
        ),
        Index("ix_mail_review_attachment_review_id", "review_id"),
    )


class MailIdempotencyRow(Base):
    """One row per ``Idempotency-Key`` actually used, scoped to its mailbox.

    ``result_version`` and ``result_note_id`` are the review's version and
    ``note_id`` right after this command completed. ``MailIdempotencyLinkRow``
    snapshots the *entire* attachment link set as of that same moment — not
    only the parts this particular command newly linked, since an earlier
    ``approve`` already contributed some of that set before a later
    ``attachments/approve`` added more. Replays report exactly that snapshot,
    never whatever the review has grown into since (a later command's extra
    links, or a later ``promote-to-note``'s ``note_id``).
    """

    __tablename__ = "mail_idempotency_keys"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    mailbox_key: Mapped[str] = mapped_column(String(64), nullable=False)
    message_id: Mapped[str] = mapped_column(String(255), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(200), nullable=False)
    actor_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    action: Mapped[str] = mapped_column(String(30), nullable=False)
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    #: RESTRICT, not CASCADE: an idempotency record is a historical fact about
    #: a command that already ran. Deleting its review must never silently
    #: take the audit trail of that command down with it.
    review_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("mail_reviews.id", ondelete="RESTRICT"), nullable=False
    )
    result_version: Mapped[int] = mapped_column(Integer, nullable=False)
    #: The review's ``note_id`` at the moment *this* command finished — almost
    #: always ``NULL``, since promotion is its own, non-idempotent endpoint.
    #: Replaying an approve/dismiss/attachments-approve command must report
    #: the snapshot it produced, not whatever the review has since been
    #: promoted to.
    result_note_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )

    __table_args__ = (
        UniqueConstraint("mailbox_key", "idempotency_key", name="uq_mail_idempotency_key"),
        Index("ix_mail_idempotency_review_id", "review_id"),
        Index("ix_mail_idempotency_actor_id", "actor_id"),
    )


class MailIdempotencyLinkRow(Base):
    """Which attachment rows a given idempotent command actually linked."""

    __tablename__ = "mail_idempotency_links"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    #: RESTRICT: these two rows are the historical record of exactly which
    #: attachment a given idempotent command linked. Neither side should be
    #: deletable out from under that record.
    idempotency_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("mail_idempotency_keys.id", ondelete="RESTRICT"), nullable=False
    )
    review_attachment_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("mail_review_attachments.id", ondelete="RESTRICT"), nullable=False
    )

    __table_args__ = (
        UniqueConstraint(
            "idempotency_id", "review_attachment_id", name="uq_mail_idempotency_link"
        ),
        Index("ix_mail_idempotency_link_review_attachment_id", "review_attachment_id"),
    )


class MailAuditRow(Base):
    """Structured audit trail for review decisions and attachment downloads.

    Never carries a message body, attachment content, or free-text PII —
    only identifiers, the actor, the trace ID, and the command's shape.
    """

    __tablename__ = "mail_audit_log"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    actor_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    action: Mapped[str] = mapped_column(String(30), nullable=False)
    mailbox_key: Mapped[str] = mapped_column(String(64), nullable=False)
    message_id: Mapped[str] = mapped_column(String(255), nullable=False)
    part_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    payload_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    trace_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )

    __table_args__ = (
        Index("ix_mail_audit_message", "mailbox_key", "message_id"),
        Index("ix_mail_audit_actor_id", "actor_id"),
    )
