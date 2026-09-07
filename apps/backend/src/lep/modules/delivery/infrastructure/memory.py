"""In-memory delivery adapter (ADR-018).

목업 데이터다. 실제 고객·직원 정보가 아니다. AGENTS.md 1절 7항.

Task and milestone codes are shared vocabulary: TSK-1038 appears on screens 02,
03, 04 and 07, and M3 on 03, 06 and 08. Other modules reference these by string
rather than importing anything from here.
"""

from __future__ import annotations

from datetime import date

from ..domain.entities import Clause, Confidence, Milestone, Statement, Task, TaskStatus

PRJ_DAON = "prj-daon"

_MILESTONES: list[Milestone] = [
    Milestone(
        id="ms-m1",
        project_id=PRJ_DAON,
        code="M1",
        name="요구정의",
        status=TaskStatus.DONE,
        progress_percent=100,
        start=date(2026, 3, 1),
        end=date(2026, 4, 30),
    ),
    Milestone(
        id="ms-m2",
        project_id=PRJ_DAON,
        code="M2",
        name="설계",
        status=TaskStatus.DONE,
        progress_percent=100,
        start=date(2026, 5, 1),
        end=date(2026, 6, 30),
    ),
    Milestone(
        id="ms-m3",
        project_id=PRJ_DAON,
        code="M3",
        name="개발·검수",
        status=TaskStatus.IN_PROGRESS,
        progress_percent=72,
        start=date(2026, 7, 1),
        end=date(2026, 9, 12),
    ),
    Milestone(
        id="ms-m4",
        project_id=PRJ_DAON,
        code="M4",
        name="오픈",
        status=TaskStatus.PLANNED,
        progress_percent=0,
        start=date(2026, 10, 1),
        end=date(2026, 12, 31),
    ),
]

_TASKS: list[Task] = [
    Task(
        id="tsk-1038",
        project_id=PRJ_DAON,
        code="TSK-1038",
        title="IF 정의서 v2",
        milestone_id="ms-m2",
        status=TaskStatus.BLOCKED,
        start=date(2026, 6, 1),
        end=date(2026, 7, 15),
        assignee="박도윤",
        blocked_reason="WMS 필드 매핑 표 미확정. WMS팀 회신 대기 중.",
        blocked_owner="박도윤",
    ),
    Task(
        id="tsk-1042",
        project_id=PRJ_DAON,
        code="TSK-1042",
        title="검수 시나리오 작성",
        milestone_id="ms-m3",
        status=TaskStatus.IN_PROGRESS,
        start=date(2026, 7, 20),
        end=date(2026, 9, 12),
        assignee="이서영",
    ),
    Task(
        id="tsk-1050",
        project_id=PRJ_DAON,
        code="TSK-1050",
        title="API 게이트웨이 성능 테스트",
        milestone_id="ms-m3",
        status=TaskStatus.DONE,
        start=date(2026, 8, 1),
        end=date(2026, 9, 1),
        assignee="박도윤",
    ),
    Task(
        id="tsk-1051",
        project_id=PRJ_DAON,
        code="TSK-1051",
        title="배포 스크립트 리팩터링",
        milestone_id="ms-m3",
        status=TaskStatus.IN_PROGRESS,
        start=date(2026, 8, 10),
        end=date(2026, 9, 25),
        assignee="김서준",
    ),
    Task(
        id="tsk-1071",
        project_id=PRJ_DAON,
        code="TSK-1071",
        title="배포 파이프라인 (WBS 외 커밋)",
        milestone_id=None,
        status=TaskStatus.VCS_ONLY,
        start=date(2026, 8, 20),
        end=date(2026, 9, 6),
        assignee=None,
        vcs_ref="PR #221",
    ),
]

_STATEMENTS: list[Statement] = [
    Statement(
        id="stm-daon-v1",
        project_id=PRJ_DAON,
        filename="과업지시서_다온물산_v1.hwpx",
        clause_count=41,
        classified_count=18,
        analysed=True,
    )
]

_CLAUSES: list[Clause] = [
    Clause(
        id="cls-3-2",
        statement_id="stm-daon-v1",
        article="제3조 2항",
        task_title="WMS 연동 인터페이스 정의",
        category="설계",
        confidence=Confidence.HIGH,
        wbs_mapping="M2 · TSK-1038",
        promoted_task_id="tsk-1038",
    ),
    Clause(
        id="cls-4-1",
        statement_id="stm-daon-v1",
        article="제4조 1항",
        task_title="검수 시나리오 작성 및 실행",
        category="검수",
        confidence=Confidence.HIGH,
        wbs_mapping="M3 · TSK-1042",
        promoted_task_id="tsk-1042",
    ),
    Clause(
        id="cls-5-3",
        statement_id="stm-daon-v1",
        article="제5조 3항",
        task_title='"운영 안정화 지원" 범위 산정',
        category="미분류",
        confidence=Confidence.LOW,
        wbs_mapping=None,
    ),
    Clause(
        id="cls-6",
        statement_id="stm-daon-v1",
        article="제6조",
        task_title="월간 진행 보고서 제출",
        category="보고",
        confidence=Confidence.HIGH,
        wbs_mapping="M1–M4 반복",
    ),
    Clause(
        id="cls-8-2",
        statement_id="stm-daon-v1",
        article="제8조 2항",
        task_title='"보안성 검토" 대상·기준 불명확',
        category="미분류",
        confidence=Confidence.LOW,
        wbs_mapping=None,
    ),
]

_NEXT_CODE = [1100]


class InMemoryDeliveryRepository:
    def list_milestones(self, project_id: str) -> list[Milestone]:
        return [item for item in _MILESTONES if item.project_id == project_id]

    def list_tasks(self, project_id: str) -> list[Task]:
        return [item for item in _TASKS if item.project_id == project_id]

    def get_task(self, task_id: str) -> Task | None:
        return next((item for item in _TASKS if item.id == task_id), None)

    def find_task_by_code(self, code: str) -> Task | None:
        return next((item for item in _TASKS if item.code == code), None)

    def add_task(self, task: Task) -> Task:
        _TASKS.append(task)
        return task

    def replace_task(self, task: Task) -> Task:
        for index, existing in enumerate(_TASKS):
            if existing.id == task.id:
                _TASKS[index] = task
                return task
        _TASKS.append(task)
        return task

    def get_milestone(self, milestone_id: str) -> Milestone | None:
        return next((item for item in _MILESTONES if item.id == milestone_id), None)

    def replace_milestone(self, milestone: Milestone) -> Milestone:
        for index, existing in enumerate(_MILESTONES):
            if existing.id == milestone.id:
                _MILESTONES[index] = milestone
                return milestone
        _MILESTONES.append(milestone)
        return milestone

    def list_statements(self, project_id: str) -> list[Statement]:
        return [item for item in _STATEMENTS if item.project_id == project_id]

    def get_statement(self, statement_id: str) -> Statement | None:
        return next((item for item in _STATEMENTS if item.id == statement_id), None)

    def list_clauses(self, statement_id: str) -> list[Clause]:
        return [item for item in _CLAUSES if item.statement_id == statement_id]

    def get_clause(self, clause_id: str) -> Clause | None:
        return next((item for item in _CLAUSES if item.id == clause_id), None)

    def replace_clause(self, clause: Clause) -> Clause:
        for index, existing in enumerate(_CLAUSES):
            if existing.id == clause.id:
                _CLAUSES[index] = clause
                return clause
        _CLAUSES.append(clause)
        return clause

    def next_task_code(self) -> str:
        _NEXT_CODE[0] += 1
        return f"TSK-{_NEXT_CODE[0]}"

    def tasks_ending_on_or_after(self, project_id: str, boundary: date) -> list[Task]:
        # A task that already finished is not dragged by a later milestone move,
        # and neither is one that ends before the old milestone date.
        return [
            item
            for item in _TASKS
            if item.project_id == project_id
            and item.end >= boundary
            and item.status is not TaskStatus.DONE
        ]
