"""Project use cases."""

from __future__ import annotations

from ....common.problems import not_found
from ..domain.entities import Project, ProjectSummary
from ..domain.repositories import ProjectRepository


class ProjectService:
    def __init__(self, repository: ProjectRepository) -> None:
        self._repository = repository

    def list_projects(self) -> list[Project]:
        return self._repository.list_projects()

    def get_project(self, project_id: str) -> Project:
        project = self._repository.get_project(project_id)
        if project is None:
            raise not_found(f"프로젝트를 찾을 수 없습니다: {project_id}")
        return project

    def get_summary(self, project_id: str) -> ProjectSummary:
        # Confirm the project exists first so a missing summary and a missing
        # project produce the same, honest 404 rather than an empty card.
        self.get_project(project_id)
        summary = self._repository.get_summary(project_id)
        if summary is None:
            raise not_found(f"프로젝트 요약을 찾을 수 없습니다: {project_id}")
        return summary

    def exists(self, project_id: str) -> bool:
        return self._repository.get_project(project_id) is not None
