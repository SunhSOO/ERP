"""Project use cases.

Projects are created by people, not seeded. A fresh installation has none, and
the home screen says so rather than showing invented demo rows.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as DbSession

from ....common.db import as_utc
from ....common.problems import ProblemError, not_found
from ..domain.entities import CODE_PATTERN, Project, ProjectSummary, SyncHealth, ViewRole
from ..infrastructure.models import ProjectRow

#: 코드를 비워 두면 이름에서 만들어 준다. 사용자가 매번 규칙을 외울 필요는 없다.
_SLUG_STRIP = str.maketrans({" ": "-", "/": "-", "\\": "-", ".": "-"})


def derive_code(name: str) -> str:
    base = name.strip().translate(_SLUG_STRIP)
    base = "".join(ch for ch in base if ch.isalnum() or ch in "-_")
    return (base[:30] or "PRJ").upper()


def _to_project(row: ProjectRow) -> Project:
    return Project(
        id=row.id,
        code=row.code,
        name=row.name,
        customer_name=row.customer_name,
        role=ViewRole(row.role),
        pm_name=row.pm_name,
        created_by=row.created_by,
        created_at=as_utc(row.created_at),
        archived=row.archived,
    )


class ProjectService:
    def __init__(self, db: DbSession) -> None:
        self._db = db

    def list_projects(self, *, include_archived: bool = False) -> list[Project]:
        """모든 인증 사용자가 모든 프로젝트를 본다.

        30명 규모의 사내 도구라 프로젝트는 공유 자산이다. 프로젝트별 접근 제한이
        필요해지면 RBAC와 함께 들어온다.
        """

        stmt = select(ProjectRow).order_by(ProjectRow.created_at.desc())
        if not include_archived:
            stmt = stmt.where(ProjectRow.archived.is_(False))
        return [_to_project(row) for row in self._db.scalars(stmt).all()]

    def get_project(self, project_id: str) -> Project:
        row = self._db.get(ProjectRow, project_id)
        if row is None:
            raise not_found(f"프로젝트를 찾을 수 없습니다: {project_id}")
        return _to_project(row)

    def create_project(
        self,
        *,
        name: str,
        code: str | None,
        customer_name: str,
        role: str,
        pm_name: str,
        created_by: str,
    ) -> Project:
        clean_name = name.strip()
        if not clean_name:
            raise ProblemError("VALIDATION_FAILED", "프로젝트 이름을 입력해 주세요.")

        clean_code = (code or "").strip() or derive_code(clean_name)
        if not CODE_PATTERN.match(clean_code):
            raise ProblemError(
                "VALIDATION_FAILED",
                "프로젝트 코드는 영문·숫자·하이픈·밑줄만 쓸 수 있고 "
                "2자 이상 40자 이하여야 합니다.",
            )

        try:
            view_role = ViewRole(role)
        except ValueError as exc:
            raise ProblemError(
                "VALIDATION_FAILED", "역할은 vendor 또는 client여야 합니다."
            ) from exc

        row = ProjectRow(
            id=str(uuid.uuid4()),
            code=clean_code,
            name=clean_name,
            customer_name=customer_name.strip(),
            role=view_role.value,
            pm_name=pm_name.strip(),
            created_by=created_by,
            created_at=datetime.now(tz=UTC),
        )
        self._db.add(row)
        try:
            self._db.flush()
        except IntegrityError as exc:
            self._db.rollback()
            raise ProblemError(
                "STATE_CONFLICT", f"이미 쓰이고 있는 프로젝트 코드입니다: {clean_code}"
            ) from exc

        return _to_project(row)

    def archive_project(self, project_id: str) -> Project:
        """물리 삭제하지 않는다. ADR-013."""

        row = self._db.get(ProjectRow, project_id)
        if row is None:
            raise not_found(f"프로젝트를 찾을 수 없습니다: {project_id}")
        row.archived = True
        self._db.flush()
        return _to_project(row)

    def exists(self, project_id: str) -> bool:
        return self._db.get(ProjectRow, project_id) is not None

    def count(self) -> int:
        return (
            self._db.scalar(
                select(func.count())
                .select_from(ProjectRow)
                .where(ProjectRow.archived.is_(False))
            )
            or 0
        )

    def summary(self, project_id: str, *, task_count: int, statement_count: int,
                progress: int | None, vault: tuple[SyncHealth, str],
                mail_unclassified: int, vcs: tuple[SyncHealth, str]) -> ProjectSummary:
        """카드에 쓸 집계.

        각 수치는 그것을 소유한 모듈이 계산해 넘긴다. 이 모듈은 조립만 한다.
        대시보드 전용 계산 규칙을 만들지 않는다는 03_MODULE_SPECIFICATIONS 1.4절
        규칙이다.
        """

        self.get_project(project_id)
        vault_health, vault_note = vault
        vcs_health, vcs_note = vcs
        return ProjectSummary(
            project_id=project_id,
            wbs_progress_percent=progress,
            schedule_note=None if progress is not None else "아직 WBS가 없습니다",
            vault_health=vault_health,
            vault_note=vault_note,
            unclassified_mail_count=mail_unclassified,
            vcs_health=vcs_health,
            vcs_note=vcs_note,
            task_count=task_count,
            statement_count=statement_count,
        )
