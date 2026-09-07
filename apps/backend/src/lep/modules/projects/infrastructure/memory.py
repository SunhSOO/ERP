"""In-memory project adapter (ADR-018).

목업 데이터다. 실제 고객·직원 정보가 아니다. AGENTS.md 1절 7항.
회사와 인명은 목업이 쓰던 가상 이름을 그대로 옮겼다.

Writes mutate this store, so the screens are genuinely interactive. Restarting the
server resets it. WP-PKD-020 replaces this with PostgreSQL.
"""

from __future__ import annotations

from ..domain.entities import Project, ProjectSummary, SyncHealth, ViewRole

#: Stable IDs. Other modules reference projects by these strings rather than
#: importing anything from this module's internals.
PRJ_DAON = "prj-daon"
PRJ_HANBIT = "prj-hanbit"
PRJ_CHEONGRAM = "prj-cheongram"

_PROJECTS: list[Project] = [
    Project(
        id=PRJ_DAON,
        code="PRJ-2026-001",
        name="다온물산 물류 통합",
        customer_name="다온물산",
        role=ViewRole.VENDOR,
        pm_name="김서준",
    ),
    Project(
        id=PRJ_HANBIT,
        code="PRJ-2026-002",
        name="한빛테크 MES 고도화",
        customer_name="한빛테크",
        role=ViewRole.VENDOR,
        pm_name="김서준",
    ),
    Project(
        id=PRJ_CHEONGRAM,
        code="PRJ-2026-003",
        name="청람소프트 마이그레이션",
        customer_name="청람소프트",
        role=ViewRole.CLIENT,
        pm_name="박도윤",
    ),
]

_SUMMARIES: dict[str, ProjectSummary] = {
    PRJ_DAON: ProjectSummary(
        project_id=PRJ_DAON,
        wbs_progress_percent=72,
        schedule_note=None,
        vault_health=SyncHealth.OK,
        vault_note="동기화됨",
        unclassified_mail_count=3,
        vcs_health=SyncHealth.MISMATCH,
        vcs_note="불일치 2",
    ),
    PRJ_HANBIT: ProjectSummary(
        project_id=PRJ_HANBIT,
        wbs_progress_percent=54,
        schedule_note=None,
        vault_health=SyncHealth.OK,
        vault_note="동기화됨",
        unclassified_mail_count=0,
        vcs_health=SyncHealth.OK,
        vcs_note="정합",
    ),
    PRJ_CHEONGRAM: ProjectSummary(
        project_id=PRJ_CHEONGRAM,
        wbs_progress_percent=None,
        schedule_note="일정 지연",
        vault_health=SyncHealth.STALE,
        vault_note="동기화 12시간 전",
        unclassified_mail_count=0,
        vcs_health=SyncHealth.MISMATCH,
        vcs_note="불일치 5",
    ),
}


class InMemoryProjectRepository:
    def list_projects(self) -> list[Project]:
        return list(_PROJECTS)

    def get_project(self, project_id: str) -> Project | None:
        return next((project for project in _PROJECTS if project.id == project_id), None)

    def get_summary(self, project_id: str) -> ProjectSummary | None:
        return _SUMMARIES.get(project_id)
