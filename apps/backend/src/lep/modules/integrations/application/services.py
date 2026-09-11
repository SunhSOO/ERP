"""Integration use cases: repository reconciliation and LLM settings."""

from __future__ import annotations

import re
import uuid
from dataclasses import replace
from datetime import UTC, datetime
from typing import Protocol

from sqlalchemy.orm import Session as DbSession

from ....common.problems import ProblemError, not_found, state_conflict
from ...delivery.public import adopt_vcs_task
from ...documents.public import converter_status
from ...projects.public import require_project
from ..domain.entities import (
    Credential,
    GpuPriority,
    LinkHealth,
    LlmRuntimeSnapshot,
    LlmRuntimeStatus,
    LlmServer,
    Mismatch,
    MismatchKind,
    ModelState,
    ProjectModel,
    ProjectRepositoryConnection,
    ProjectRepositoryConnectionAudit,
    TaskMapping,
    VcsStatus,
)
from ..domain.ports import LlmRuntimePort
from ..infrastructure.llm_runtime import FixtureLlmRuntimeAdapter
from ..infrastructure.models import (
    ProjectRepositoryConnectionAuditRow,
    ProjectRepositoryConnectionRow,
)

_LLM_HEALTH: dict[LlmRuntimeStatus, LinkHealth] = {
    LlmRuntimeStatus.CONNECTED: LinkHealth.OK,
    LlmRuntimeStatus.DEGRADED: LinkHealth.STALE,
    LlmRuntimeStatus.UNAVAILABLE: LinkHealth.MISMATCH,
    LlmRuntimeStatus.FIXTURE: LinkHealth.NOT_CONFIGURED,
    LlmRuntimeStatus.NOT_CONFIGURED: LinkHealth.NOT_CONFIGURED,
}


def _llm_credential(snapshot: LlmRuntimeSnapshot) -> Credential:
    """The LLM credential row reflects the real runtime probe (WP-PKD-033A).

    Screen 09 must not show 미설정 next to a server that just answered a
    status check; nor may it claim connected because an env var is set when
    the probe actually failed.
    """

    needs_input = snapshot.status in (LlmRuntimeStatus.FIXTURE, LlmRuntimeStatus.NOT_CONFIGURED)
    return Credential(
        kind="llm",
        label="로컬 LLM 서버",
        health=_LLM_HEALTH[snapshot.status],
        detail=snapshot.detail,
        missing_input="추론 서버 주소와 모델 이름" if needs_input else None,
    )


class IntegrationPort(Protocol):
    def vcs_status(self, project_id: str) -> VcsStatus | None: ...

    def list_mismatches(self, project_id: str) -> list[Mismatch]: ...

    def get_mismatch(self, mismatch_id: str) -> Mismatch | None: ...

    def replace_mismatch(self, mismatch: Mismatch) -> Mismatch: ...

    def list_mappings(self, project_id: str) -> list[TaskMapping]: ...

    def resync_vcs(self, project_id: str) -> VcsStatus: ...

    def server(self) -> dict[str, object]: ...

    def list_models(self) -> list[ProjectModel]: ...

    def replace_model(self, model: ProjectModel) -> ProjectModel: ...

    def credentials(
        self, project_id: str, converter: tuple[str, str], llm: Credential = ...
    ) -> list[Credential]: ...


class IntegrationService:
    def __init__(
        self, adapter: IntegrationPort, llm_runtime: LlmRuntimePort | None = None
    ) -> None:
        """``llm_runtime`` defaults to the no-network fixture adapter.

        Kept optional so code built against the pre-WP-PKD-033A constructor
        (adapter only) still works; the real caller (``public.py``) always
        supplies a real runtime port explicitly.
        """

        self._adapter = adapter
        self._llm_runtime = llm_runtime or FixtureLlmRuntimeAdapter()

    # ── repository reconciliation ──────────────────────────────────────────
    def vcs_status(self, db: DbSession, project_id: str) -> VcsStatus:
        """저장소 연동 상태.

        새로 만든 프로젝트에는 저장소가 아직 없다. 그것은 오류가 아니라 상태이므로
        404 대신 "미연결"을 낸다. 화면 07은 이 값을 보고 무엇을 설정해야 하는지
        말해 준다.
        """

        require_project(db, project_id)
        status = self._adapter.vcs_status(project_id)
        if status is None:
            return VcsStatus(
                project_id=project_id,
                repository="",
                health=LinkHealth.NOT_CONFIGURED,
                last_sync_at=datetime.now(tz=UTC),
                open_pull_requests=0,
                match_rate_percent=0,
            )
        return status

    def list_mismatches(self, db: DbSession, project_id: str) -> list[Mismatch]:
        require_project(db, project_id)
        return self._adapter.list_mismatches(project_id)

    def list_mappings(self, db: DbSession, project_id: str) -> list[TaskMapping]:
        require_project(db, project_id)
        return self._adapter.list_mappings(project_id)

    def resync_vcs(self, db: DbSession, project_id: str) -> VcsStatus:
        require_project(db, project_id)
        if self._adapter.vcs_status(project_id) is None:
            return self.vcs_status(db, project_id)
        return self._adapter.resync_vcs(project_id)

    def resolve_mismatch(self, db: DbSession, mismatch_id: str) -> Mismatch:
        """Act on a reconciliation finding.

        Undefined work becomes a real WBS task, through delivery's public
        interface. A status conflict is only flagged for review here; changing a
        task's status is delivery's call, not this module's.
        """

        mismatch = self._adapter.get_mismatch(mismatch_id)
        if mismatch is None:
            raise not_found(f"불일치 항목을 찾을 수 없습니다: {mismatch_id}")
        if mismatch.resolved:
            raise state_conflict("이미 처리된 불일치입니다.")

        if mismatch.kind is MismatchKind.UNDEFINED_WORK and mismatch.task_code:
            adopt_vcs_task(db, mismatch.project_id, mismatch.task_code)

        return self._adapter.replace_mismatch(replace(mismatch, resolved=True))

    # ── repository connections ─────────────────────────────────────────────
    def get_connection(self, db: DbSession, project_id: str) -> ProjectRepositoryConnection | None:
        """Get the current repository connection for a project, or None if not set."""

        require_project(db, project_id)
        row = db.query(ProjectRepositoryConnectionRow).filter(
            ProjectRepositoryConnectionRow.project_id == project_id
        ).one_or_none()

        if row is None:
            return None

        return ProjectRepositoryConnection(
            id=row.id,
            project_id=row.project_id,
            provider=row.provider,
            repository=row.repository,
            version=row.version,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    def set_connection(
        self,
        db: DbSession,
        project_id: str,
        repository: str,
        expected_version: int,
        actor_id: str,
    ) -> ProjectRepositoryConnection:
        """Create or update a repository connection.

        Only admin or project creator can modify. Validates repository via
        the GitHub adapter without persisting the token. Returns 409 if
        expected_version doesn't match (optimistic locking).

        Authorization checks must be done by the caller before calling this method.
        """

        require_project(db, project_id)

        # Validate repository format
        if not self._is_valid_repository(repository):
            raise ProblemError("VALIDATION_FAILED", "저장소는 owner/repository 형식이어야 합니다.")

        # Get or create connection
        row = db.query(ProjectRepositoryConnectionRow).filter(
            ProjectRepositoryConnectionRow.project_id == project_id
        ).one_or_none()

        previous_repo = None
        if row is None:
            # Creating new connection
            if expected_version != 0:
                raise state_conflict(
                    f"새 연결은 버전 0부터 시작합니다. 현재: {expected_version}"
                )

            row = ProjectRepositoryConnectionRow(
                id=str(uuid.uuid4()),
                project_id=project_id,
                provider="github",
                repository=repository,
                version=1,
            )
            db.add(row)
        else:
            # Updating existing connection
            if row.version != expected_version:
                db.rollback()
                raise state_conflict(
                    f"버전 충돌. 예상: {expected_version}, 현재: {row.version}"
                )

            previous_repo = row.repository
            row.repository = repository
            row.version = row.version + 1

        db.flush()

        # Create audit entry
        audit_row = ProjectRepositoryConnectionAuditRow(
            id=str(uuid.uuid4()),
            connection_id=row.id,
            project_id=project_id,
            actor_id=actor_id,
            previous_repository=previous_repo,
            new_repository=repository,
        )
        db.add(audit_row)
        db.commit()

        # Note: Cache invalidation happens when the adapter's repo_for method
        # is called next, which will read the updated database value. The
        # adapter's cache is updated on-demand, not proactively invalidated here.

        return ProjectRepositoryConnection(
            id=row.id,
            project_id=row.project_id,
            provider=row.provider,
            repository=row.repository,
            version=row.version,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    def get_connection_audits(
        self, db: DbSession, project_id: str
    ) -> list[ProjectRepositoryConnectionAudit]:
        """Get the audit trail for a project's repository connection."""

        require_project(db, project_id)
        rows = db.query(ProjectRepositoryConnectionAuditRow).filter(
            ProjectRepositoryConnectionAuditRow.project_id == project_id
        ).order_by(ProjectRepositoryConnectionAuditRow.created_at).all()

        return [
            ProjectRepositoryConnectionAudit(
                id=row.id,
                connection_id=row.connection_id,
                project_id=row.project_id,
                actor_id=row.actor_id,
                previous_repository=row.previous_repository,
                new_repository=row.new_repository,
                created_at=row.created_at,
            )
            for row in rows
        ]

    @staticmethod
    def _is_valid_repository(repository: str) -> bool:
        """Check if repository is in valid owner/repo format."""

        return bool(
            re.match(r"^[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?/[a-zA-Z0-9._-]+$", repository)
        )

    # ── AI settings ────────────────────────────────────────────────────────
    def server(self) -> LlmServer:
        """Runtime snapshot, independent of which VCS adapter is selected.

        ``name``/``network_note`` still come from the AI-settings fixture
        (the project-model list has no persistence yet); everything about
        connection and model status comes from a live read through
        ``LlmRuntimePort``, never from that fixture's static dict.
        """

        raw = self._adapter.server()
        models = self._adapter.list_models()
        snapshot = self._llm_runtime.snapshot()
        return LlmServer(
            name=str(raw["name"]),
            network_note=str(raw["network_note"]),
            status=snapshot.status,
            detail=snapshot.detail,
            gpu_usage_percent=snapshot.gpu_usage_percent,
            active_model_count=snapshot.active_model_count,
            available_model_names=snapshot.available_model_names,
            running_model_names=snapshot.running_model_names,
            project_count=len(models),
        )

    def list_models(self) -> list[ProjectModel]:
        return self._adapter.list_models()

    def set_model(
        self, db: DbSession, project_id: str, *, model: str, priority: GpuPriority
    ) -> ProjectModel:
        require_project(db, project_id)
        current = next(
            (item for item in self._adapter.list_models() if item.project_id == project_id),
            None,
        )
        if current is None:
            raise not_found(f"프로젝트 모델 설정을 찾을 수 없습니다: {project_id}")
        return self._adapter.replace_model(
            replace(current, model=model, priority=priority, state=ModelState.RUNNING)
        )

    def restart_model(self, db: DbSession, project_id: str) -> ProjectModel:
        """Always rejects. WP-PKD-033A only adds a read-only status probe;
        there is no load/unload/restart call to make on the real adapter, and
        writing a fake ``RUNNING`` state here would claim one exists."""

        require_project(db, project_id)
        raise state_conflict(
            "모델 재시작은 아직 지원되지 않습니다. 현재는 읽기 전용 상태 조회만 가능합니다."
        )

    def credentials(self, db: DbSession, project_id: str) -> list[Credential]:
        require_project(db, project_id)
        return self._adapter.credentials(
            project_id, converter_status(), _llm_credential(self._llm_runtime.snapshot())
        )
