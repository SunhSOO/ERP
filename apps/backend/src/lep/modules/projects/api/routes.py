"""Project HTTP routes."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict

from ....common.envelope import Envelope, ListEnvelope, collection, single
from ...mail.public import unclassified_count
from ..domain.entities import Project, ProjectSummary
from ..public import get_project_service

router = APIRouter(prefix="/api/v1/projects", tags=["projects"])


class ProjectOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    code: str
    name: str
    customer_name: str
    role: str
    pm_name: str

    @classmethod
    def of(cls, project: Project) -> ProjectOut:
        return cls(
            id=project.id,
            code=project.code,
            name=project.name,
            customer_name=project.customer_name,
            role=project.role.value,
            pm_name=project.pm_name,
        )


class ProjectSummaryOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_id: str
    wbs_progress_percent: int | None
    schedule_note: str | None
    vault_health: str
    vault_note: str
    unclassified_mail_count: int
    vcs_health: str
    vcs_note: str

    @classmethod
    def of(cls, summary: ProjectSummary) -> ProjectSummaryOut:
        return cls(
            project_id=summary.project_id,
            wbs_progress_percent=summary.wbs_progress_percent,
            schedule_note=summary.schedule_note,
            vault_health=summary.vault_health.value,
            vault_note=summary.vault_note,
            unclassified_mail_count=summary.unclassified_mail_count,
            vcs_health=summary.vcs_health.value,
            vcs_note=summary.vcs_note,
        )


@router.get("", response_model=ListEnvelope[ProjectOut])
async def list_projects() -> ListEnvelope[ProjectOut]:
    projects = get_project_service().list_projects()
    return collection([ProjectOut.of(project) for project in projects], total=len(projects))


@router.get("/{project_id}", response_model=Envelope[ProjectOut])
async def get_project(project_id: str) -> Envelope[ProjectOut]:
    return single(ProjectOut.of(get_project_service().get_project(project_id)))


@router.get("/{project_id}/summary", response_model=Envelope[ProjectSummaryOut])
async def get_project_summary(project_id: str) -> Envelope[ProjectSummaryOut]:
    summary = ProjectSummaryOut.of(get_project_service().get_summary(project_id))
    # The mail count is owned by the mail module, so it is read live through that
    # module's public interface rather than copied into the project's own record.
    # Dismissing a message on screen 06 therefore updates this card immediately.
    # WP-PKD-020 replaces the live read with an event-fed projection.
    summary = summary.model_copy(
        update={"unclassified_mail_count": unclassified_count(project_id)}
    )
    return single(summary)
