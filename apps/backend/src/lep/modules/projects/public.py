"""Stable public interface for the projects module.

Other modules confirm a project exists through here and never touch its table.
The database session is passed in rather than opened here, so a request that
spans two modules stays inside one transaction.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session as DbSession

from .application.services import ProjectService

__all__ = ["ProjectRef", "get_project_service", "project_exists", "require_project"]


@dataclass(frozen=True, slots=True)
class ProjectRef:
    """The minimum another module may know about a project."""

    id: str
    code: str
    name: str


def get_project_service(db: DbSession) -> ProjectService:
    return ProjectService(db)


def project_exists(db: DbSession, project_id: str) -> bool:
    return ProjectService(db).exists(project_id)


def require_project(db: DbSession, project_id: str) -> ProjectRef:
    """Raise ``NOT_FOUND`` unless the project exists, then hand back its reference."""

    project = ProjectService(db).get_project(project_id)
    return ProjectRef(id=project.id, code=project.code, name=project.name)
