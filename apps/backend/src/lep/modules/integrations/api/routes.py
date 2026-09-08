"""Integration HTTP routes: repository reconciliation and AI settings."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session as DbSession

from ....common.db import get_session
from ....common.envelope import Envelope, ListEnvelope, collection, single
from ...iam.public import CurrentUser
from ..domain.entities import (
    Credential,
    GpuPriority,
    LlmServer,
    Mismatch,
    ProjectModel,
    TaskMapping,
    VcsStatus,
)
from ..public import get_integration_service

router = APIRouter(prefix="/api/v1", tags=["integrations"])


class VcsStatusOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    repository: str
    health: str
    last_sync_at: datetime
    open_pull_requests: int
    match_rate_percent: int

    @classmethod
    def of(cls, item: VcsStatus) -> VcsStatusOut:
        return cls(
            repository=item.repository,
            health=item.health.value,
            last_sync_at=item.last_sync_at,
            open_pull_requests=item.open_pull_requests,
            match_rate_percent=item.match_rate_percent,
        )


class MismatchOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    kind: str
    title: str
    detail: str
    task_code: str | None
    vcs_ref: str
    resolved: bool

    @classmethod
    def of(cls, item: Mismatch) -> MismatchOut:
        return cls(
            id=item.id,
            kind=item.kind.value,
            title=item.title,
            detail=item.detail,
            task_code=item.task_code,
            vcs_ref=item.vcs_ref,
            resolved=item.resolved,
        )


class MappingOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_code: str | None
    task_title: str
    vcs_ref: str
    task_status: str
    aligned: bool

    @classmethod
    def of(cls, item: TaskMapping) -> MappingOut:
        return cls(
            task_code=item.task_code,
            task_title=item.task_title,
            vcs_ref=item.vcs_ref,
            task_status=item.task_status,
            aligned=item.aligned,
        )


class ServerOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    network_note: str
    gpu_usage_percent: int
    active_model_count: int
    project_count: int

    @classmethod
    def of(cls, item: LlmServer) -> ServerOut:
        return cls(
            name=item.name,
            network_note=item.network_note,
            gpu_usage_percent=item.gpu_usage_percent,
            active_model_count=item.active_model_count,
            project_count=item.project_count,
        )


class ModelOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_id: str
    project_name: str
    model: str | None
    state: str
    priority: str | None
    gpu_share_percent: int | None

    @classmethod
    def of(cls, item: ProjectModel) -> ModelOut:
        return cls(
            project_id=item.project_id,
            project_name=item.project_name,
            model=item.model,
            state=item.state.value,
            priority=item.priority.value if item.priority else None,
            gpu_share_percent=item.gpu_share_percent,
        )


class CredentialOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: str
    label: str
    health: str
    detail: str
    missing_input: str | None

    @classmethod
    def of(cls, item: Credential) -> CredentialOut:
        return cls(
            kind=item.kind,
            label=item.label,
            health=item.health.value,
            detail=item.detail,
            missing_input=item.missing_input,
        )


class SetModelRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model: str
    priority: GpuPriority


@router.get("/projects/{project_id}/vcs", response_model=Envelope[VcsStatusOut])
async def get_vcs(
    project_id: str,
    user: CurrentUser,
    db: Annotated[DbSession, Depends(get_session)],
) -> Envelope[VcsStatusOut]:
    return single(VcsStatusOut.of(get_integration_service().vcs_status(db, project_id)))


@router.post("/projects/{project_id}/vcs/sync", response_model=Envelope[VcsStatusOut])
async def resync_vcs(
    project_id: str,
    user: CurrentUser,
    db: Annotated[DbSession, Depends(get_session)],
) -> Envelope[VcsStatusOut]:
    return single(VcsStatusOut.of(get_integration_service().resync_vcs(db, project_id)))


@router.get(
    "/projects/{project_id}/vcs/mismatches", response_model=ListEnvelope[MismatchOut]
)
async def list_mismatches(
    project_id: str,
    user: CurrentUser,
    db: Annotated[DbSession, Depends(get_session)],
) -> ListEnvelope[MismatchOut]:
    items = get_integration_service().list_mismatches(db, project_id)
    return collection([MismatchOut.of(item) for item in items], total=len(items))


@router.get("/projects/{project_id}/vcs/mappings", response_model=ListEnvelope[MappingOut])
async def list_mappings(
    project_id: str,
    user: CurrentUser,
    db: Annotated[DbSession, Depends(get_session)],
) -> ListEnvelope[MappingOut]:
    items = get_integration_service().list_mappings(db, project_id)
    return collection([MappingOut.of(item) for item in items], total=len(items))


@router.post("/vcs/mismatches/{mismatch_id}/resolve", response_model=Envelope[MismatchOut])
async def resolve_mismatch(
    mismatch_id: str,
    user: CurrentUser,
    db: Annotated[DbSession, Depends(get_session)],
) -> Envelope[MismatchOut]:
    return single(MismatchOut.of(get_integration_service().resolve_mismatch(db, mismatch_id)))


@router.get("/ai/server", response_model=Envelope[ServerOut])
async def get_server(user: CurrentUser) -> Envelope[ServerOut]:
    return single(ServerOut.of(get_integration_service().server()))


@router.get("/ai/models", response_model=ListEnvelope[ModelOut])
async def list_models(user: CurrentUser) -> ListEnvelope[ModelOut]:
    items = get_integration_service().list_models()
    return collection([ModelOut.of(item) for item in items], total=len(items))


@router.put("/projects/{project_id}/ai/model", response_model=Envelope[ModelOut])
async def set_model(
    project_id: str,
    request: SetModelRequest,
    user: CurrentUser,
    db: Annotated[DbSession, Depends(get_session)],
) -> Envelope[ModelOut]:
    updated = get_integration_service().set_model(
        db, project_id, model=request.model, priority=request.priority
    )
    return single(ModelOut.of(updated))


@router.post("/projects/{project_id}/ai/restart", response_model=Envelope[ModelOut])
async def restart_model(
    project_id: str,
    user: CurrentUser,
    db: Annotated[DbSession, Depends(get_session)],
) -> Envelope[ModelOut]:
    return single(ModelOut.of(get_integration_service().restart_model(db, project_id)))


@router.get(
    "/projects/{project_id}/integrations", response_model=ListEnvelope[CredentialOut]
)
async def list_credentials(
    project_id: str,
    user: CurrentUser,
    db: Annotated[DbSession, Depends(get_session)],
) -> ListEnvelope[CredentialOut]:
    items = get_integration_service().credentials(db, project_id)
    return collection([CredentialOut.of(item) for item in items], total=len(items))
