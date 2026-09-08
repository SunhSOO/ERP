"""Stable public interface for the delivery module."""

from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session as DbSession

from .application.services import DeliveryService, DeliverySummary
from .domain.entities import ScheduleShift

__all__ = [
    "DeliverySummary",
    "ScheduleShift",
    "adopt_vcs_task",
    "find_milestone_id_by_code",
    "get_delivery_service",
    "preview_milestone_shift",
    "project_delivery_summary",
    "shift_milestone",
    "task_codes_and_status",
]


def get_delivery_service(db: DbSession) -> DeliveryService:
    return DeliveryService(db)


def project_delivery_summary(db: DbSession, project_id: str) -> DeliverySummary:
    """홈 카드가 쓰는 집계. 태스크가 없으면 진행률은 ``None``이다."""

    return DeliveryService(db).summary(project_id)


def task_codes_and_status(db: DbSession, project_id: str) -> list[tuple[str, str, str]]:
    """저장소 정합 계산에 넘길 ``(code, title, status)`` 목록."""

    return [
        (t.code, t.title, t.status.value)
        for t in DeliveryService(db).list_tasks(project_id)
    ]


def find_milestone_id_by_code(db: DbSession, project_id: str, code: str) -> str | None:
    for milestone in DeliveryService(db).list_milestones(project_id):
        if milestone.code == code:
            return milestone.id
    return None


def preview_milestone_shift(
    db: DbSession, milestone_id: str, new_end: date
) -> list[ScheduleShift]:
    return DeliveryService(db).preview_milestone_shift(milestone_id, new_end)


def shift_milestone(db: DbSession, milestone_id: str, new_end: date) -> list[ScheduleShift]:
    return DeliveryService(db).shift_milestone(milestone_id, new_end)


def adopt_vcs_task(db: DbSession, project_id: str, task_code: str) -> str:
    return DeliveryService(db).adopt_vcs_task(project_id, task_code).code
