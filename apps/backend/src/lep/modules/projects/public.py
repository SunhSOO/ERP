"""Stable public interface for the projects module.

Other modules import this file and nothing else from ``projects``.
``scripts/check_boundaries.py`` rejects any deeper import.

Delivery, knowledge, documents, mail and integrations all need to confirm a
project exists before they answer for it. That check goes through
:func:`project_exists` rather than through anyone's tables.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from .application.services import ProjectService
from .infrastructure.memory import InMemoryProjectRepository

__all__ = ["ProjectRef", "get_project_service", "project_exists", "require_project"]


@dataclass(frozen=True, slots=True)
class ProjectRef:
    """The minimum another module may know about a project."""

    id: str
    code: str
    name: str


@lru_cache(maxsize=1)
def get_project_service() -> ProjectService:
    """The module's composition root.

    ADR-018 puts adapter selection behind configuration. Only the in-memory
    adapter exists today, so there is nothing to branch on yet.
    """

    return ProjectService(InMemoryProjectRepository())


def project_exists(project_id: str) -> bool:
    return get_project_service().exists(project_id)


def require_project(project_id: str) -> ProjectRef:
    """Raise ``NOT_FOUND`` unless the project exists, then hand back its reference."""

    project = get_project_service().get_project(project_id)
    return ProjectRef(id=project.id, code=project.code, name=project.name)
