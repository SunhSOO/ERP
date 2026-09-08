"""Delivery use cases: statements of work, clauses, tasks, milestones.

Nothing here is seeded. A new project has no statement, no clause and no task
until someone uploads a document or adds a task.

The schedule-shift calculation is shared by the preview and the apply path, so
what the confirm dialog promises is what the apply actually does.
"""

from __future__ import annotations

import os
import re
import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as DbSession

from ....common.problems import ProblemError, not_found, state_conflict
from ...projects.public import require_project
from ..domain.entities import (
    Clause,
    Confidence,
    Milestone,
    ScheduleShift,
    Statement,
    Task,
    TaskStatus,
)
from ..infrastructure.models import ClauseRow, MilestoneRow, StatementRow, TaskRow
from ..infrastructure.statement_parser import SUPPORTED_SUFFIXES, parse


#: 업로드 원본이 놓이는 볼륨. 컨테이너에서는 /data/uploads로 마운트된다.
def upload_root() -> Path:
    return Path(os.getenv("LEP_UPLOAD_DIR", ".uploads"))


#: 한 번에 받는 최대 크기. 과업지시서는 보통 수 MB다.
MAX_UPLOAD_BYTES = 50 * 1024 * 1024

_SAFE_NAME = re.compile(r"[^A-Za-z0-9가-힣._-]+")


def safe_filename(name: str) -> str:
    """경로 조각을 떼고 파일 이름만 남긴다.

    ``../../etc/passwd`` 같은 값이 그대로 경로에 붙지 않게 한다.
    """

    base = Path(name).name
    cleaned = _SAFE_NAME.sub("_", base).strip("._") or "upload"
    return cleaned[:200]


@dataclass(frozen=True, slots=True)
class DeliverySummary:
    task_count: int
    statement_count: int
    milestone_count: int
    progress_percent: int | None


def _to_task(row: TaskRow) -> Task:
    return Task(
        id=row.id,
        project_id=row.project_id,
        code=row.code,
        title=row.title,
        milestone_id=row.milestone_id,
        status=TaskStatus(row.status),
        start=row.start,
        end=row.end,
        assignee=row.assignee,
        blocked_reason=row.blocked_reason,
        blocked_owner=row.blocked_owner,
        vcs_ref=row.vcs_ref,
    )


def _to_milestone(row: MilestoneRow) -> Milestone:
    return Milestone(
        id=row.id,
        project_id=row.project_id,
        code=row.code,
        name=row.name,
        status=TaskStatus(row.status),
        progress_percent=row.progress_percent,
        start=row.start,
        end=row.end,
    )


def _to_statement(row: StatementRow) -> Statement:
    return Statement(
        id=row.id,
        project_id=row.project_id,
        filename=row.filename,
        clause_count=row.clause_count,
        classified_count=row.classified_count,
        analysed=row.analysed,
    )


def _to_clause(row: ClauseRow) -> Clause:
    return Clause(
        id=row.id,
        statement_id=row.statement_id,
        article=row.article,
        task_title=row.task_title,
        category=row.category,
        confidence=Confidence(row.confidence),
        wbs_mapping=row.wbs_mapping,
        promoted_task_id=row.promoted_task_id,
    )


class DeliveryService:
    def __init__(self, db: DbSession) -> None:
        self._db = db

    # ── reads ──────────────────────────────────────────────────────────────
    def list_milestones(self, project_id: str) -> list[Milestone]:
        require_project(self._db, project_id)
        rows = self._db.scalars(
            select(MilestoneRow)
            .where(MilestoneRow.project_id == project_id)
            .order_by(MilestoneRow.start)
        ).all()
        return [_to_milestone(r) for r in rows]

    def list_tasks(self, project_id: str) -> list[Task]:
        require_project(self._db, project_id)
        rows = self._db.scalars(
            select(TaskRow).where(TaskRow.project_id == project_id).order_by(TaskRow.start)
        ).all()
        return [_to_task(r) for r in rows]

    def list_statements(self, project_id: str) -> list[Statement]:
        require_project(self._db, project_id)
        rows = self._db.scalars(
            select(StatementRow)
            .where(StatementRow.project_id == project_id)
            .order_by(StatementRow.uploaded_at.desc())
        ).all()
        return [_to_statement(r) for r in rows]

    def get_statement(self, statement_id: str) -> Statement:
        row = self._db.get(StatementRow, statement_id)
        if row is None:
            raise not_found(f"과업지시서를 찾을 수 없습니다: {statement_id}")
        return _to_statement(row)

    def statement_error(self, statement_id: str) -> str | None:
        row = self._db.get(StatementRow, statement_id)
        return row.parse_error if row is not None else None

    def list_clauses(self, statement_id: str) -> list[Clause]:
        if self._db.get(StatementRow, statement_id) is None:
            raise not_found(f"과업지시서를 찾을 수 없습니다: {statement_id}")
        rows = self._db.scalars(
            select(ClauseRow)
            .where(ClauseRow.statement_id == statement_id)
            .order_by(ClauseRow.ordinal)
        ).all()
        return [_to_clause(r) for r in rows]

    def get_milestone(self, milestone_id: str) -> Milestone:
        row = self._db.get(MilestoneRow, milestone_id)
        if row is None:
            raise not_found(f"마일스톤을 찾을 수 없습니다: {milestone_id}")
        return _to_milestone(row)

    def summary(self, project_id: str) -> DeliverySummary:
        tasks = self._db.scalars(
            select(TaskRow).where(TaskRow.project_id == project_id)
        ).all()
        statements = (
            self._db.scalar(
                select(func.count())
                .select_from(StatementRow)
                .where(StatementRow.project_id == project_id)
            )
            or 0
        )
        milestones = (
            self._db.scalar(
                select(func.count())
                .select_from(MilestoneRow)
                .where(MilestoneRow.project_id == project_id)
            )
            or 0
        )

        # 태스크가 없으면 진행률이 없다. 0%는 "시작 안 함"이라는 뜻이라 다르다.
        countable = [t for t in tasks if t.status != TaskStatus.VCS_ONLY.value]
        progress: int | None = None
        if countable:
            done = len([t for t in countable if t.status == TaskStatus.DONE.value])
            progress = round(done / len(countable) * 100)

        return DeliverySummary(
            task_count=len(tasks),
            statement_count=statements,
            milestone_count=milestones,
            progress_percent=progress,
        )

    # ── 과업지시서 업로드 ──────────────────────────────────────────────────
    def upload_statement(
        self, project_id: str, *, filename: str, content: bytes, uploaded_by: str
    ) -> Statement:
        """업로드된 문서를 저장하고 조항으로 쪼갠다.

        파싱이 실패해도 레코드는 남기고 사유를 기록한다. 사용자가 무엇을 올렸고
        왜 안 됐는지 알아야 다시 시도할지 판단할 수 있다.
        """

        project = require_project(self._db, project_id)

        if not content:
            raise ProblemError("VALIDATION_FAILED", "빈 파일입니다.")
        if len(content) > MAX_UPLOAD_BYTES:
            raise ProblemError(
                "VALIDATION_FAILED",
                f"파일이 너무 큽니다. {MAX_UPLOAD_BYTES // (1024 * 1024)}MB 이하만 "
                "올릴 수 있습니다.",
            )

        clean = safe_filename(filename)
        suffix = Path(clean).suffix.lower()
        if suffix not in SUPPORTED_SUFFIXES:
            raise ProblemError(
                "VALIDATION_FAILED",
                f"지원하지 않는 형식입니다: {suffix or '확장자 없음'}. "
                f"{', '.join(sorted(SUPPORTED_SUFFIXES))}만 올릴 수 있습니다.",
            )

        statement_id = str(uuid.uuid4())
        relative = Path(project.code) / f"{statement_id}{suffix}"
        target = upload_root() / relative
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
        except OSError as exc:
            raise ProblemError("INTERNAL_ERROR", f"파일을 저장하지 못했습니다: {exc}") from exc

        result = parse(target)

        row = StatementRow(
            id=statement_id,
            project_id=project_id,
            filename=clean,
            stored_path=str(relative).replace("\\", "/"),
            size_bytes=len(content),
            clause_count=len(result.clauses),
            # 분류는 로컬 LLM이 붙는 WP-PKD-033의 일이다. 지금은 0이 정직하다.
            classified_count=0,
            analysed=result.succeeded,
            parse_error=result.error,
            uploaded_by=uploaded_by,
            uploaded_at=datetime.now(tz=UTC),
        )
        self._db.add(row)

        for parsed in result.clauses:
            self._db.add(
                ClauseRow(
                    id=str(uuid.uuid4()),
                    statement_id=statement_id,
                    ordinal=parsed.ordinal,
                    article=parsed.article,
                    task_title=parsed.text,
                    category="미분류",
                    confidence=Confidence.LOW.value,
                    wbs_mapping=None,
                )
            )
        self._db.flush()
        return _to_statement(row)

    # ── writes ─────────────────────────────────────────────────────────────
    def promote_clause(self, clause_id: str) -> Task:
        """조항을 WBS 태스크로 올린다.

        신뢰도가 낮은 조항은 거부한다. 지금은 분류기가 없어 모든 조항이 낮음이라
        사람이 카테고리를 정해 주기 전까지는 자동 반영되지 않는다. 화면의
        "검토 필요" 표시가 그래서 참이 된다.
        """

        clause = self._db.get(ClauseRow, clause_id)
        if clause is None:
            raise not_found(f"조항을 찾을 수 없습니다: {clause_id}")
        if clause.promoted_task_id is not None:
            raise state_conflict("이미 WBS에 반영된 조항입니다.")
        if clause.confidence == Confidence.LOW.value:
            raise state_conflict(
                "신뢰도가 낮은 조항입니다. 사람이 확인한 뒤에 WBS에 반영할 수 있습니다."
            )

        statement = self._db.get(StatementRow, clause.statement_id)
        if statement is None:
            raise not_found("과업지시서를 찾을 수 없습니다.")

        task = self._create_task(
            project_id=statement.project_id,
            title=clause.task_title[:300],
            start=date.today(),
            end=date.today() + timedelta(days=14),
        )
        clause.promoted_task_id = task.id
        clause.wbs_mapping = task.code
        self._db.flush()
        return task

    def create_task(
        self,
        project_id: str,
        *,
        title: str,
        start: date,
        end: date,
        milestone_id: str | None = None,
        assignee: str | None = None,
    ) -> Task:
        require_project(self._db, project_id)
        if not title.strip():
            raise ProblemError("VALIDATION_FAILED", "태스크 제목을 입력해 주세요.")
        if end < start:
            raise ProblemError("VALIDATION_FAILED", "종료일이 시작일보다 빠릅니다.")
        return self._create_task(
            project_id=project_id,
            title=title.strip(),
            start=start,
            end=end,
            milestone_id=milestone_id,
            assignee=assignee,
        )

    def _create_task(
        self,
        *,
        project_id: str,
        title: str,
        start: date,
        end: date,
        milestone_id: str | None = None,
        assignee: str | None = None,
    ) -> Task:
        used = (
            self._db.scalar(
                select(func.count()).select_from(TaskRow).where(TaskRow.project_id == project_id)
            )
            or 0
        )
        for attempt in range(used + 1, used + 50):
            code = f"TSK-{attempt:04d}"
            row = TaskRow(
                id=str(uuid.uuid4()),
                project_id=project_id,
                code=code,
                title=title,
                milestone_id=milestone_id,
                status=TaskStatus.PLANNED.value,
                start=start,
                end=end,
                assignee=assignee,
            )
            self._db.add(row)
            try:
                self._db.flush()
            except IntegrityError:
                # 같은 코드가 이미 있으면 다음 번호로 넘어간다.
                self._db.rollback()
                continue
            return _to_task(row)
        raise ProblemError("INTERNAL_ERROR", "태스크 코드를 배정하지 못했습니다.")

    def preview_milestone_shift(self, milestone_id: str, new_end: date) -> list[ScheduleShift]:
        """이 마일스톤 기한이 밀리면 무엇이 함께 밀리는지. 읽기 전용이다."""

        milestone = self.get_milestone(milestone_id)
        delta = new_end - milestone.end
        if delta == timedelta(0):
            return []

        followers = self._db.scalars(
            select(TaskRow).where(
                TaskRow.project_id == milestone.project_id,
                TaskRow.end >= milestone.end,
                TaskRow.status != TaskStatus.DONE.value,
            )
        ).all()
        return [
            ScheduleShift(
                task_code=t.code,
                task_title=t.title,
                old_end=t.end,
                new_end=t.end + delta,
            )
            for t in followers
        ]

    def shift_milestone(self, milestone_id: str, new_end: date) -> list[ScheduleShift]:
        milestone = self.get_milestone(milestone_id)
        shifts = self.preview_milestone_shift(milestone_id, new_end)
        delta = new_end - milestone.end

        row = self._db.get(MilestoneRow, milestone_id)
        assert row is not None
        row.end = new_end

        for shift in shifts:
            task = self._db.scalar(
                select(TaskRow).where(
                    TaskRow.project_id == milestone.project_id, TaskRow.code == shift.task_code
                )
            )
            if task is not None:
                task.start = task.start + delta
                task.end = task.end + delta
        self._db.flush()
        return shifts

    def adopt_vcs_task(self, project_id: str, task_code: str) -> Task:
        row = self._db.scalar(
            select(TaskRow).where(TaskRow.project_id == project_id, TaskRow.code == task_code)
        )
        if row is None:
            raise not_found(f"태스크를 찾을 수 없습니다: {task_code}")
        if row.status != TaskStatus.VCS_ONLY.value:
            raise state_conflict("WBS에 이미 정의된 태스크입니다.")
        row.status = TaskStatus.PLANNED.value
        self._db.flush()
        return _to_task(row)
