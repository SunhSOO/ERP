"""SQLAlchemy tables owned by the delivery module.

Statements of work, the clauses parsed out of them, and the WBS they feed.
"""

from __future__ import annotations

from datetime import UTC, date, datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
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


class MilestoneRow(Base):
    __tablename__ = "milestones"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    code: Mapped[str] = mapped_column(String(20), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="planned")
    progress_percent: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    start: Mapped[date] = mapped_column(Date, nullable=False)
    end: Mapped[date] = mapped_column(Date, nullable=False)

    __table_args__ = (
        UniqueConstraint("project_id", "code", name="uq_milestone_project_code"),
    )


class TaskRow(Base):
    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    code: Mapped[str] = mapped_column(String(30), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    milestone_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("milestones.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="planned")
    start: Mapped[date] = mapped_column(Date, nullable=False)
    end: Mapped[date] = mapped_column(Date, nullable=False)
    assignee: Mapped[str | None] = mapped_column(String(100), nullable=True)
    #: BLOCKED에는 사유와 해소 담당자가 있어야 한다. 검증은 application이 한다.
    blocked_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    blocked_owner: Mapped[str | None] = mapped_column(String(100), nullable=True)
    vcs_ref: Mapped[str | None] = mapped_column(String(120), nullable=True)

    __table_args__ = (UniqueConstraint("project_id", "code", name="uq_task_project_code"),)


class StatementRow(Base):
    __tablename__ = "statements"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    filename: Mapped[str] = mapped_column(String(300), nullable=False)
    #: 업로드 볼륨 안의 상대 경로.
    stored_path: Mapped[str] = mapped_column(String(500), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    clause_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    classified_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    analysed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    #: 파싱이 실패했으면 사유를 남긴다. 성공으로 숨기지 않는다.
    parse_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    uploaded_by: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )

    __table_args__ = (Index("ix_statements_project_id", "project_id"),)


class ClauseRow(Base):
    __tablename__ = "clauses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    statement_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("statements.id", ondelete="CASCADE"), nullable=False
    )
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    article: Mapped[str] = mapped_column(String(100), nullable=False)
    task_title: Mapped[str] = mapped_column(Text, nullable=False)
    #: 절의 본문 전체. 분류할 때 모델에 넘기는 입력이고, 재분류할 때 원본
    #: 문서를 다시 읽지 않아도 되게 한다. 스캔본은 다시 읽으면 OCR을 다시 돈다.
    body: Mapped[str] = mapped_column(Text, nullable=False, default="")
    #: 십진 번호의 깊이와 상위 절. 화면의 트리와 볼트의 링크가 이걸 쓴다.
    level: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    parent: Mapped[str | None] = mapped_column(String(40), nullable=True)
    category: Mapped[str] = mapped_column(String(40), nullable=False, default="미분류")
    confidence: Mapped[str] = mapped_column(String(10), nullable=False, default="low")
    #: 수행해서 완료할 수 있는 일인지. 계약 조건은 거짓이다.
    actionable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    #: 분류기가 그렇게 판단한 근거. 분류하지 못했으면 그 사유가 들어간다.
    #: 사람이 검토할 때 읽는 값이라 비워 두지 않는다.
    classified_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    #: 어느 분류기가 답했는지. 픽스처와 실제 모델을 화면에서 구분한다.
    classified_by: Mapped[str | None] = mapped_column(String(80), nullable=True)
    wbs_mapping: Mapped[str | None] = mapped_column(String(120), nullable=True)
    promoted_task_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True
    )

    __table_args__ = (Index("ix_clauses_statement_id", "statement_id"),)
