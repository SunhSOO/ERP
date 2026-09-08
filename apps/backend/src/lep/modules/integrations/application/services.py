"""Integration use cases: repository reconciliation and LLM settings."""

from __future__ import annotations

from dataclasses import replace
from typing import Protocol

from ....common.problems import not_found, state_conflict
from ...delivery.public import adopt_vcs_task
from ...documents.public import converter_status
from ...projects.public import require_project
from ..domain.entities import (
    Credential,
    GpuPriority,
    LlmServer,
    Mismatch,
    MismatchKind,
    ModelState,
    ProjectModel,
    TaskMapping,
    VcsStatus,
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
        self, project_id: str, converter: tuple[str, str]
    ) -> list[Credential]: ...


class IntegrationService:
    def __init__(self, adapter: IntegrationPort) -> None:
        self._adapter = adapter

    # ── repository reconciliation ──────────────────────────────────────────
    def vcs_status(self, project_id: str) -> VcsStatus:
        require_project(project_id)
        status = self._adapter.vcs_status(project_id)
        if status is None:
            raise not_found(f"깃허브 연동 정보를 찾을 수 없습니다: {project_id}")
        return status

    def list_mismatches(self, project_id: str) -> list[Mismatch]:
        require_project(project_id)
        return self._adapter.list_mismatches(project_id)

    def list_mappings(self, project_id: str) -> list[TaskMapping]:
        require_project(project_id)
        return self._adapter.list_mappings(project_id)

    def resync_vcs(self, project_id: str) -> VcsStatus:
        require_project(project_id)
        return self._adapter.resync_vcs(project_id)

    def resolve_mismatch(self, mismatch_id: str) -> Mismatch:
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
            adopt_vcs_task(mismatch.task_code)

        return self._adapter.replace_mismatch(replace(mismatch, resolved=True))

    # ── AI settings ────────────────────────────────────────────────────────
    def server(self) -> LlmServer:
        raw = self._adapter.server()
        models = self._adapter.list_models()
        return LlmServer(
            name=str(raw["name"]),
            network_note=str(raw["network_note"]),
            gpu_usage_percent=int(str(raw["gpu_usage_percent"])),
            active_model_count=len(
                [model for model in models if model.state is ModelState.RUNNING]
            ),
            project_count=len(models),
        )

    def list_models(self) -> list[ProjectModel]:
        return self._adapter.list_models()

    def set_model(
        self, project_id: str, *, model: str, priority: GpuPriority
    ) -> ProjectModel:
        require_project(project_id)
        current = next(
            (item for item in self._adapter.list_models() if item.project_id == project_id),
            None,
        )
        if current is None:
            raise not_found(f"프로젝트 모델 설정을 찾을 수 없습니다: {project_id}")
        return self._adapter.replace_model(
            replace(current, model=model, priority=priority, state=ModelState.RUNNING)
        )

    def restart_model(self, project_id: str) -> ProjectModel:
        require_project(project_id)
        current = next(
            (item for item in self._adapter.list_models() if item.project_id == project_id),
            None,
        )
        if current is None:
            raise not_found(f"프로젝트 모델 설정을 찾을 수 없습니다: {project_id}")
        if current.model is None:
            raise state_conflict("모델이 설정되지 않아 재시작할 수 없습니다.")
        return self._adapter.replace_model(replace(current, state=ModelState.RUNNING))

    def credentials(self, project_id: str) -> list[Credential]:
        require_project(project_id)
        return self._adapter.credentials(project_id, converter_status())
