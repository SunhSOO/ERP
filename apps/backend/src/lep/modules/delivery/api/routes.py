"""Delivery HTTP routes: statements, clauses, tasks, milestones, WBS."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict

from ....common.envelope import Envelope, ListEnvelope, collection, single
from ..domain.entities import Clause, Milestone, ScheduleShift, Statement, Task
from ..public import get_delivery_service

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
    def of(cls, item: Milestone) -> MilestoneOut:
        return cls(
            id=item.id,
            code=item.code,
            name=item.name,
            status=item.status.value,
            progress_percent=item.progress_percent,
            start=item.start,
            end=item.end,
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
    def of(cls, item: Task) -> TaskOut:
        return cls(
            id=item.id,
            code=item.code,
            title=item.title,
            milestone_id=item.milestone_id,
            status=item.status.value,
            start=item.start,
            end=item.end,
            assignee=item.assignee,
            blocked_reason=item.blocked_reason,
            blocked_owner=item.blocked_owner,
            vcs_ref=item.vcs_ref,
        )


class StatementOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    filename: str
    clause_count: int
    classified_count: int
    analysed: bool

    @classmethod
    def of(cls, item: Statement) -> StatementOut:
        return cls(
            id=item.id,
            filename=item.filename,
            clause_count=item.clause_count,
            classified_count=item.classified_count,
            analysed=item.analysed,
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
    def of(cls, item: Clause) -> ClauseOut:
        return cls(
            id=item.id,
            article=item.article,
            task_title=item.task_title,
            category=item.category,
            confidence=item.confidence.value,
            wbs_mapping=item.wbs_mapping,
            promoted_task_id=item.promoted_task_id,
        )


class ScheduleShiftOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_code: str
    task_title: str
    old_end: date
    new_end: date

    @classmethod
    def of(cls, item: ScheduleShift) -> ScheduleShiftOut:
        return cls(
            task_code=item.task_code,
            task_title=item.task_title,
            old_end=item.old_end,
            new_end=item.new_end,
        )


class ShiftRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    new_end: date
    #: When true the change is calculated but not applied. The confirm dialog on
    #: screen 08 uses this before asking the user.
    dry_run: bool = True


@router.get("/projects/{project_id}/milestones", response_model=ListEnvelope[MilestoneOut])
async def list_milestones(project_id: str) -> ListEnvelope[MilestoneOut]:
    items = get_delivery_service().list_milestones(project_id)
    return collection([MilestoneOut.of(item) for item in items], total=len(items))


@router.get("/projects/{project_id}/tasks", response_model=ListEnvelope[TaskOut])
async def list_tasks(project_id: str) -> ListEnvelope[TaskOut]:
    items = get_delivery_service().list_tasks(project_id)
    return collection([TaskOut.of(item) for item in items], total=len(items))


@router.get("/projects/{project_id}/statements", response_model=ListEnvelope[StatementOut])
async def list_statements(project_id: str) -> ListEnvelope[StatementOut]:
    items = get_delivery_service().list_statements(project_id)
    return collection([StatementOut.of(item) for item in items], total=len(items))


@router.get("/statements/{statement_id}/clauses", response_model=ListEnvelope[ClauseOut])
async def list_clauses(statement_id: str) -> ListEnvelope[ClauseOut]:
    items = get_delivery_service().list_clauses(statement_id)
    return collection([ClauseOut.of(item) for item in items], total=len(items))


@router.post("/clauses/{clause_id}/promote-to-task", response_model=Envelope[TaskOut])
async def promote_clause(clause_id: str) -> Envelope[TaskOut]:
    return single(TaskOut.of(get_delivery_service().promote_clause(clause_id)))


@router.post(
    "/milestones/{milestone_id}/shift", response_model=ListEnvelope[ScheduleShiftOut]
)
async def shift_milestone(
    milestone_id: str, request: ShiftRequest
) -> ListEnvelope[ScheduleShiftOut]:
    """Preview or apply a milestone date change.

    ``dry_run`` defaults to true so an accidental call cannot move a schedule.
    """

    service = get_delivery_service()
    shifts = (
        service.preview_milestone_shift(milestone_id, request.new_end)
        if request.dry_run
        else service.shift_milestone(milestone_id, request.new_end)
    )
    return collection([ScheduleShiftOut.of(shift) for shift in shifts], total=len(shifts))
