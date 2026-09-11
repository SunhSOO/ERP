"""SQLAlchemy tables owned by the integrations module."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from ....common.db import Base


def utc_now() -> datetime:
    return datetime.now(tz=UTC)


class ProjectRepositoryConnectionRow(Base):
    __tablename__ = "project_repository_connections"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    provider: Mapped[str] = mapped_column(String(20), nullable=False, default="github")
    repository: Mapped[str] = mapped_column(String(255), nullable=False)
    version: Mapped[int] = mapped_column(default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )

    __table_args__ = (
        Index("ix_project_repository_connections_project_id", "project_id"),
    )


class ProjectRepositoryConnectionAuditRow(Base):
    __tablename__ = "project_repository_connection_audits"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    connection_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("project_repository_connections.id", ondelete="CASCADE"),
        nullable=False,
    )
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    actor_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    previous_repository: Mapped[str | None] = mapped_column(String(255), nullable=True)
    new_repository: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )

    __table_args__ = (
        Index("ix_project_repository_connection_audits_connection_id", "connection_id"),
        Index("ix_project_repository_connection_audits_project_id", "project_id"),
        Index("ix_project_repository_connection_audits_actor_id", "actor_id"),
    )
