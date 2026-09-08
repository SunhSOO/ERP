"""Storage ports for the projects module.

Protocols, not base classes. The in-memory adapter used through WP-PKD-013 and the
SQL adapter added in WP-PKD-020 both satisfy this without inheriting anything.
"""

from __future__ import annotations

from typing import Protocol

from .entities import Project, ProjectSummary


class ProjectRepository(Protocol):
    def list_projects(self) -> list[Project]: ...

    def get_project(self, project_id: str) -> Project | None: ...

    def get_summary(self, project_id: str) -> ProjectSummary | None: ...
