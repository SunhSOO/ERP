"""Project HTTP routes. Everything here requires a logged-in user."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session as DbSession

from ....common.db import get_session
from ....common.envelope import Envelope, ListEnvelope, collection, single
from ...delivery.public import project_delivery_summary
from ...iam.public import CurrentUser
from ...knowledge.public import ensure_project_vault, project_vault_summary
from ...mail.public import unclassified_count
from ..application.services import ProjectService
from ..domain.entities import Project, ProjectSummary, SyncHealth

router = APIRouter(prefix="/api/v1/projects", tags=["projects"])


class ProjectOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    code: str
    name: str
    customer_name: str
    role: str
    pm_name: str
    created_at: datetime

    @classmethod
    def of(cls, p: Project) -> ProjectOut:
        return cls(
            id=p.id,
            code=p.code,
            name=p.name,
            customer_name=p.customer_name,
            role=p.role.value,
            pm_name=p.pm_name,
            created_at=p.created_at,
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
    task_count: int
    statement_count: int

    @classmethod
    def of(cls, s: ProjectSummary) -> ProjectSummaryOut:
        return cls(
            project_id=s.project_id,
            wbs_progress_percent=s.wbs_progress_percent,
            schedule_note=s.schedule_note,
            vault_health=s.vault_health.value,
            vault_note=s.vault_note,
            unclassified_mail_count=s.unclassified_mail_count,
            vcs_health=s.vcs_health.value,
            vcs_note=s.vcs_note,
            task_count=s.task_count,
            statement_count=s.statement_count,
        )


class CreateProjectRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=200)
    #: 비우면 이름에서 만들어 준다.
    code: str | None = Field(default=None, max_length=40)
    customer_name: str = Field(default="", max_length=200)
    role: str = Field(default="vendor")
    pm_name: str = Field(default="", max_length=100)


@router.get("", response_model=ListEnvelope[ProjectOut])
def list_projects(
    user: CurrentUser,
    db: Annotated[DbSession, Depends(get_session)],
) -> ListEnvelope[ProjectOut]:
    items = ProjectService(db).list_projects()
    return collection([ProjectOut.of(p) for p in items], total=len(items))


@router.post("", response_model=Envelope[ProjectOut], status_code=201)
def create_project(
    request: CreateProjectRequest,
    user: CurrentUser,
    db: Annotated[DbSession, Depends(get_session)],
) -> Envelope[ProjectOut]:
    project = ProjectService(db).create_project(
        name=request.name,
        code=request.code,
        customer_name=request.customer_name,
        role=request.role,
        pm_name=request.pm_name or user.display_name,
        created_by=user.id,
    )
    # 프로젝트마다 볼트 폴더를 하나 만든다. 지식이 프로젝트 경계를 넘지 않는다.
    ensure_project_vault(project.id, project.code)
    return single(ProjectOut.of(project))


@router.get("/{project_id}", response_model=Envelope[ProjectOut])
def get_project(
    project_id: str,
    user: CurrentUser,
    db: Annotated[DbSession, Depends(get_session)],
) -> Envelope[ProjectOut]:
    return single(ProjectOut.of(ProjectService(db).get_project(project_id)))


@router.post("/{project_id}/archive", response_model=Envelope[ProjectOut])
def archive_project(
    project_id: str,
    user: CurrentUser,
    db: Annotated[DbSession, Depends(get_session)],
) -> Envelope[ProjectOut]:
    return single(ProjectOut.of(ProjectService(db).archive_project(project_id)))


@router.get("/{project_id}/summary", response_model=Envelope[ProjectSummaryOut])
def project_summary(
    project_id: str,
    user: CurrentUser,
    db: Annotated[DbSession, Depends(get_session)],
) -> Envelope[ProjectSummaryOut]:
    """카드에 쓸 집계.

    각 수치는 소유 모듈의 public 인터페이스에서 온다. 여기서 새로 계산하지
    않는다.
    """

    service = ProjectService(db)
    project = service.get_project(project_id)

    delivery = project_delivery_summary(db, project_id)
    vault_health, vault_note = project_vault_summary(project.id, project.code)

    summary = service.summary(
        project_id,
        task_count=delivery.task_count,
        statement_count=delivery.statement_count,
        progress=delivery.progress_percent,
        vault=(SyncHealth(vault_health), vault_note),
        mail_unclassified=unclassified_count(project_id),
        # 저장소 연동은 프로젝트마다 따로 설정해야 한다. 아직 없으면 그렇게 말한다.
        vcs=(SyncHealth.UNKNOWN, "저장소 미연결"),
    )
    return single(ProjectSummaryOut.of(summary))
