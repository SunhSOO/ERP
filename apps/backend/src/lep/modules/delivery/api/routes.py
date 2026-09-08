"""Delivery HTTP routes: statements, clauses, tasks, milestones."""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, File, UploadFile
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session as DbSession

from ....common.db import get_session
from ....common.envelope import Envelope, ListEnvelope, collection, single
from ...iam.public import CurrentUser
from ..application.services import MAX_UPLOAD_BYTES, DeliveryService
from ..domain.entities import Clause, Milestone, ScheduleShift, Statement, Task
from ..infrastructure.statement_parser import SUPPORTED_SUFFIXES

router = APIRouter(prefix="/api/v1", tags=["delivery"])


class MilestoneOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    code: str
    name: str
    status: str
    progress_percent: int
    start: date
    end: date

    @classmethod
    def of(cls, m: Milestone) -> MilestoneOut:
        return cls(
            id=m.id, code=m.code, name=m.name, status=m.status.value,
            progress_percent=m.progress_percent, start=m.start, end=m.end,
        )


class TaskOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    code: str
    title: str
    milestone_id: str | None
    status: str
    start: date
    end: date
    assignee: str | None
    blocked_reason: str | None
    blocked_owner: str | None
    vcs_ref: str | None

    @classmethod
    def of(cls, t: Task) -> TaskOut:
        return cls(
            id=t.id, code=t.code, title=t.title, milestone_id=t.milestone_id,
            status=t.status.value, start=t.start, end=t.end, assignee=t.assignee,
            blocked_reason=t.blocked_reason, blocked_owner=t.blocked_owner,
            vcs_ref=t.vcs_ref,
        )


class StatementOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    filename: str
    clause_count: int
    classified_count: int
    analysed: bool
    parse_error: str | None = None

    @classmethod
    def of(cls, s: Statement, parse_error: str | None = None) -> StatementOut:
        return cls(
            id=s.id, filename=s.filename, clause_count=s.clause_count,
            classified_count=s.classified_count, analysed=s.analysed,
            parse_error=parse_error,
        )


class ClauseOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    article: str
    task_title: str
    category: str
    confidence: str
    wbs_mapping: str | None
    promoted_task_id: str | None

    @classmethod
    def of(cls, c: Clause) -> ClauseOut:
        return cls(
            id=c.id, article=c.article, task_title=c.task_title, category=c.category,
            confidence=c.confidence.value, wbs_mapping=c.wbs_mapping,
            promoted_task_id=c.promoted_task_id,
        )


class ScheduleShiftOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_code: str
    task_title: str
    old_end: date
    new_end: date

    @classmethod
    def of(cls, s: ScheduleShift) -> ScheduleShiftOut:
        return cls(
            task_code=s.task_code, task_title=s.task_title,
            old_end=s.old_end, new_end=s.new_end,
        )


class UploadLimitsOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    max_bytes: int
    suffixes: list[str]


class CreateTaskRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=300)
    start: date
    end: date
    milestone_id: str | None = None
    assignee: str | None = Field(default=None, max_length=100)


class ShiftRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    new_end: date
    dry_run: bool = True


@router.get("/upload-limits", response_model=Envelope[UploadLimitsOut])
def upload_limits(user: CurrentUser) -> Envelope[UploadLimitsOut]:
    """드래그 업로드 화면이 허용 형식과 크기를 화면에 표시하는 데 쓴다."""

    return single(
        UploadLimitsOut(max_bytes=MAX_UPLOAD_BYTES, suffixes=sorted(SUPPORTED_SUFFIXES))
    )


@router.get("/projects/{project_id}/milestones", response_model=ListEnvelope[MilestoneOut])
def list_milestones(
    project_id: str, user: CurrentUser, db: Annotated[DbSession, Depends(get_session)]
) -> ListEnvelope[MilestoneOut]:
    items = DeliveryService(db).list_milestones(project_id)
    return collection([MilestoneOut.of(i) for i in items], total=len(items))


@router.get("/projects/{project_id}/tasks", response_model=ListEnvelope[TaskOut])
def list_tasks(
    project_id: str, user: CurrentUser, db: Annotated[DbSession, Depends(get_session)]
) -> ListEnvelope[TaskOut]:
    items = DeliveryService(db).list_tasks(project_id)
    return collection([TaskOut.of(i) for i in items], total=len(items))


@router.post("/projects/{project_id}/tasks", response_model=Envelope[TaskOut], status_code=201)
def create_task(
    project_id: str,
    request: CreateTaskRequest,
    user: CurrentUser,
    db: Annotated[DbSession, Depends(get_session)],
) -> Envelope[TaskOut]:
    task = DeliveryService(db).create_task(
        project_id,
        title=request.title,
        start=request.start,
        end=request.end,
        milestone_id=request.milestone_id,
        assignee=request.assignee,
    )
    return single(TaskOut.of(task))


@router.get("/projects/{project_id}/statements", response_model=ListEnvelope[StatementOut])
def list_statements(
    project_id: str, user: CurrentUser, db: Annotated[DbSession, Depends(get_session)]
) -> ListEnvelope[StatementOut]:
    service = DeliveryService(db)
    items = service.list_statements(project_id)
    return collection(
        [StatementOut.of(i, service.statement_error(i.id)) for i in items], total=len(items)
    )


@router.post(
    "/projects/{project_id}/statements",
    response_model=Envelope[StatementOut],
    status_code=201,
)
async def upload_statement(
    project_id: str,
    user: CurrentUser,
    db: Annotated[DbSession, Depends(get_session)],
    file: Annotated[UploadFile, File()],
) -> Envelope[StatementOut]:
    """과업지시서를 올린다. 화면에서 드래그해 놓으면 여기로 온다.

    kordoc이 문서를 마크다운으로 바꾸고 제N조 단위로 쪼갠다. 분류는 아직
    하지 않는다. 로컬 LLM이 붙는 WP-PKD-033의 일이다.
    """

    content = await file.read()
    service = DeliveryService(db)
    statement = service.upload_statement(
        project_id,
        filename=file.filename or "upload",
        content=content,
        uploaded_by=user.id,
    )
    return single(StatementOut.of(statement, service.statement_error(statement.id)))


@router.get("/statements/{statement_id}/clauses", response_model=ListEnvelope[ClauseOut])
def list_clauses(
    statement_id: str, user: CurrentUser, db: Annotated[DbSession, Depends(get_session)]
) -> ListEnvelope[ClauseOut]:
    items = DeliveryService(db).list_clauses(statement_id)
    return collection([ClauseOut.of(i) for i in items], total=len(items))


@router.post("/clauses/{clause_id}/promote-to-task", response_model=Envelope[TaskOut])
def promote_clause(
    clause_id: str, user: CurrentUser, db: Annotated[DbSession, Depends(get_session)]
) -> Envelope[TaskOut]:
    return single(TaskOut.of(DeliveryService(db).promote_clause(clause_id)))


@router.post("/milestones/{milestone_id}/shift", response_model=ListEnvelope[ScheduleShiftOut])
def shift_milestone(
    milestone_id: str,
    request: ShiftRequest,
    user: CurrentUser,
    db: Annotated[DbSession, Depends(get_session)],
) -> ListEnvelope[ScheduleShiftOut]:
    """미리보기 또는 실제 반영. ``dry_run``이 기본 참이라 실수로 일정이 밀리지 않는다."""

    service = DeliveryService(db)
    shifts = (
        service.preview_milestone_shift(milestone_id, request.new_end)
        if request.dry_run
        else service.shift_milestone(milestone_id, request.new_end)
    )
    return collection([ScheduleShiftOut.of(s) for s in shifts], total=len(shifts))
