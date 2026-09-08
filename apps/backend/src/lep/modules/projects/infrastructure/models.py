"""SQLAlchemy tables owned by the projects module."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from ....common.db import Base


def utc_now() -> datetime:
    return datetime.now(tz=UTC)


class ProjectRow(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    #: 볼트 폴더 이름으로도 쓰이므로 파일 시스템에 안전한 문자만 받는다.
    #: 검증은 application 계층이 한다.
    code: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    customer_name: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    role: Mapped[str] = mapped_column(String(16), nullable=False, default="vendor")
    pm_name: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    created_by: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    #: 소프트 삭제. ADR-013에 따라 핵심 레코드는 물리 삭제하지 않는다.
    archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
