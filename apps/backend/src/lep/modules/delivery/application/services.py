"""Delivery use cases.

The schedule-shift calculation is shared by the preview and the apply path. The
meeting screen shows "M3 기한을 09-12에서 09-19로 바꾸면 후행 업무 2건도 밀린다"
before asking for confirmation, and that sentence has to be true, so both paths
call :meth:`DeliveryService.preview_milestone_shift`.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import date, timedelta

from ....common.problems import not_found, state_conflict
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
from ..domain.repositories import DeliveryRepository


class DeliveryService:
    def __init__(self, repository: DeliveryRepository) -> None:
        self._repository = repository

    # ── reads ──────────────────────────────────────────────────────────────
    def list_milestones(self, project_id: str) -> list[Milestone]:
        require_project(project_id)
        return self._repository.list_milestones(project_id)

    def list_tasks(self, project_id: str) -> list[Task]:
        require_project(project_id)
        return self._repository.list_tasks(project_id)

    def list_statements(self, project_id: str) -> list[Statement]:
        require_project(project_id)
        return self._repository.list_statements(project_id)

    def list_clauses(self, statement_id: str) -> list[Clause]:
        if self._repository.get_statement(statement_id) is None:
            raise not_found(f"과업지시서를 찾을 수 없습니다: {statement_id}")
        return self._repository.list_clauses(statement_id)

    def get_task(self, task_id: str) -> Task:
        task = self._repository.get_task(task_id)
        if task is None:
            raise not_found(f"태스크를 찾을 수 없습니다: {task_id}")
        return task

    def get_milestone(self, milestone_id: str) -> Milestone:
        milestone = self._repository.get_milestone(milestone_id)
        if milestone is None:
            raise not_found(f"마일스톤을 찾을 수 없습니다: {milestone_id}")
        return milestone

    # ── writes ─────────────────────────────────────────────────────────────
    def promote_clause(self, clause_id: str) -> Task:
        """Turn a classified clause into a WBS task.

        Low-confidence clauses are refused. The mockup marks them 검토 필요 and
        says a human must look first; letting the API through would make that
        label a lie.
        """

        clause = self._repository.get_clause(clause_id)
        if clause is None:
            raise not_found(f"조항을 찾을 수 없습니다: {clause_id}")
        if clause.promoted_task_id is not None:
            raise state_conflict("이미 WBS에 반영된 조항입니다.")
        if clause.confidence is Confidence.LOW:
            raise state_conflict(
                "신뢰도가 낮은 조항입니다. 사람이 확인한 뒤에 WBS에 반영할 수 있습니다."
            )

        statement = self._repository.get_statement(clause.statement_id)
        if statement is None:
            raise not_found(f"과업지시서를 찾을 수 없습니다: {clause.statement_id}")

        code = self._repository.next_task_code()
        task = Task(
            id=code.lower(),
            project_id=statement.project_id,
            code=code,
            title=clause.task_title,
            milestone_id=None,
            status=TaskStatus.PLANNED,
            start=date.today(),
            end=date.today() + timedelta(days=14),
            assignee=None,
        )
        self._repository.add_task(task)
        self._repository.replace_clause(
            replace(clause, promoted_task_id=task.id, wbs_mapping=code)
        )
        return task

    def preview_milestone_shift(self, milestone_id: str, new_end: date) -> list[ScheduleShift]:
        """What else moves if this milestone's end date moves.

        Read-only. The apply path calls this first, so the preview and the result
        can never disagree.
        """

        milestone = self.get_milestone(milestone_id)
        delta = new_end - milestone.end
        if delta == timedelta(0):
            return []

        followers = self._repository.tasks_ending_on_or_after(
            milestone.project_id, milestone.end
        )
        return [
            ScheduleShift(
                task_code=task.code,
                task_title=task.title,
                old_end=task.end,
                new_end=task.end + delta,
            )
            for task in followers
        ]

    def shift_milestone(self, milestone_id: str, new_end: date) -> list[ScheduleShift]:
        """Move a milestone and every task that follows it."""

        milestone = self.get_milestone(milestone_id)
        shifts = self.preview_milestone_shift(milestone_id, new_end)
        delta = new_end - milestone.end

        self._repository.replace_milestone(replace(milestone, end=new_end))
        for shift in shifts:
            task = self._repository.find_task_by_code(shift.task_code)
            if task is not None:
                self._repository.replace_task(
                    replace(task, start=task.start + delta, end=task.end + delta)
                )
        return shifts

    def adopt_vcs_task(self, task_code: str, milestone_id: str | None = None) -> Task:
        """Register a repository-only work item as a real WBS task."""

        task = self._repository.find_task_by_code(task_code)
        if task is None:
            raise not_found(f"태스크를 찾을 수 없습니다: {task_code}")
        if task.status is not TaskStatus.VCS_ONLY:
            raise state_conflict("WBS에 이미 정의된 태스크입니다.")
        return self._repository.replace_task(
            replace(task, status=TaskStatus.PLANNED, milestone_id=milestone_id)
        )
