"""SQLAlchemy table for approved mail attachment references (ADR-021).

Immutable metadata only: no binary content, no scan/ready claim. Approval
happens in the mail module; this table only records the identity of the
already-approved reference so the project drive can list it. ``mailbox_key``
and ``message_id`` are opaque values the mail module owns — never a
filesystem path.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from ....common.db import Base


def utc_now() -> datetime:
    return datetime.now(tz=UTC)


class MailAttachmentLinkRow(Base):
    __tablename__ = "document_mail_attachment_links"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="RESTRICT"), nullable=False
    )
    mailbox_key: Mapped[str] = mapped_column(String(128), nullable=False)
    message_id: Mapped[str] = mapped_column(String(255), nullable=False)
    part_index: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(255), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    category: Mapped[str] = mapped_column(String(20), nullable=False)
    created_by: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )

    __table_args__ = (
        UniqueConstraint(
            "mailbox_key", "message_id", "part_index", name="uq_mail_link_source_part"
        ),
        CheckConstraint("part_index >= 0", name="ck_mail_link_part_index_nonneg"),
        CheckConstraint("size_bytes >= 0", name="ck_mail_link_size_nonneg"),
        CheckConstraint("length(name) > 0", name="ck_mail_link_name_nonempty"),
        CheckConstraint("length(content_type) > 0", name="ck_mail_link_content_type_nonempty"),
        CheckConstraint("length(sha256) = 64", name="ck_mail_link_sha256_length"),
        CheckConstraint(
            "category in ('original','report','deliverable','source')",
            name="ck_mail_link_category_allowed",
        ),
        Index("ix_mail_link_project_id", "project_id"),
        Index("ix_mail_link_created_by", "created_by"),
    )
