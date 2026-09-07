"""Fixture integration adapters (ADR-018).

목업 데이터다. 실제 고객·직원 정보가 아니다. AGENTS.md 1절 7항.
자격증명 값을 담지 않는다. 설정 여부와 상태만 담는다.

Real adapters arrive in WP-PKD-031 (GitHub), WP-PKD-032 (Obsidian),
WP-PKD-033 (local LLM) and WP-PKD-034 (Hiworks). Each needs an operator-supplied
input that does not exist yet, recorded here as ``missing_input``.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime

from ....common.adapters import (
    converter_choice,
    vault_choice,
    vault_root,
)
from ..domain.entities import (
    Credential,
    GpuPriority,
    LinkHealth,
    Mismatch,
    MismatchKind,
    ModelState,
    ProjectModel,
    TaskMapping,
    VcsStatus,
)

PRJ_DAON = "prj-daon"
PRJ_HANBIT = "prj-hanbit"
PRJ_CHEONGRAM = "prj-cheongram"

_VCS: dict[str, VcsStatus] = {
    PRJ_DAON: VcsStatus(
        project_id=PRJ_DAON,
        repository="daon-corp/logistics-platform",
        health=LinkHealth.OK,
        last_sync_at=datetime(2026, 9, 7, 4, 1, tzinfo=UTC),
        open_pull_requests=4,
        match_rate_percent=91,
    )
}

_MISMATCHES: list[Mismatch] = [
    Mismatch(
        id="mis-221",
        project_id=PRJ_DAON,
        kind=MismatchKind.UNDEFINED_WORK,
        title="WBS 외 커밋 감지",
        detail=(
            'PR #221 "배포 파이프라인 개선"이 WBS에 대응하는 태스크가 없습니다. '
            "커밋 12건, 최근 활동 09-06."
        ),
        task_code="TSK-1071",
        vcs_ref="PR #221",
    ),
    Mismatch(
        id="mis-1050",
        project_id=PRJ_DAON,
        kind=MismatchKind.STATUS_CONFLICT,
        title="완료 표시됐지만 PR 미병합",
        detail=(
            'TSK-1050 "API 게이트웨이 성능 테스트"는 WBS상 완료지만 '
            "연결된 PR #218은 아직 리뷰 중입니다."
        ),
        task_code="TSK-1050",
        vcs_ref="PR #218",
    ),
]

_MAPPINGS: list[tuple[str, TaskMapping]] = [
    (PRJ_DAON, TaskMapping("TSK-1038", "IF 정의서 v2", "이슈 #94", "blocked", True)),
    (
        PRJ_DAON,
        TaskMapping("TSK-1050", "API 게이트웨이 테스트", "PR #218", "done", False),
    ),
    (
        PRJ_DAON,
        TaskMapping("TSK-1051", "배포 스크립트 리팩터링", "PR #219 · #220", "in_progress", True),
    ),
    (
        PRJ_DAON,
        TaskMapping(None, "배포 파이프라인 개선", "PR #221", "vcs_only", False),
    ),
]

_SERVER = [
    {
        "name": "사내 GPU 서버 (사내망 전용)",
        "network_note": (
            "모든 문서·메일·회의록 처리는 사내 서버의 로컬 모델에서만 이루어집니다. "
            "외부 API로 전송되지 않습니다."
        ),
        "gpu_usage_percent": 62,
    }
]

_MODELS: list[ProjectModel] = [
    ProjectModel(
        project_id=PRJ_DAON,
        project_name="다온물산 물류 통합",
        model="llama-3.1-70b-instruct (Q4)",
        state=ModelState.RUNNING,
        priority=GpuPriority.HIGH,
        gpu_share_percent=40,
    ),
    ProjectModel(
        project_id=PRJ_HANBIT,
        project_name="한빛테크 MES 고도화",
        model="llama-3.1-8b-instruct (Q8)",
        state=ModelState.RUNNING,
        priority=GpuPriority.NORMAL,
        gpu_share_percent=22,
    ),
    ProjectModel(
        project_id=PRJ_CHEONGRAM,
        project_name="청람소프트 마이그레이션",
        model=None,
        state=ModelState.STOPPED,
        priority=None,
        gpu_share_percent=None,
    ),
]


def _vault_credential() -> Credential:
    """The vault row reflects the adapter actually in use.

    Screen 09 is where an operator checks whether an integration is live. A row
    that says 미설정 while the vault is being read would be a lie.
    """

    choice = vault_choice()
    root = vault_root()
    if choice.use_real and root:
        return Credential(
            kind="vault",
            label="옵시디언 볼트",
            health=LinkHealth.OK,
            detail=f"{root}에 연결됨",
        )
    return Credential(
        kind="vault",
        label="옵시디언 볼트",
        health=LinkHealth.NOT_CONFIGURED,
        detail=choice.unavailable_reason or "볼트 경로가 아직 설정되지 않았습니다.",
        missing_input="볼트 경로",
    )


def _converter_credential(converter: tuple[str, str]) -> Credential:
    name, version = converter
    choice = converter_choice()
    detail = (
        f"버전 {version} · 실제 변환기"
        if choice.use_real
        else choice.unavailable_reason or f"버전 {version} · 픽스처"
    )
    return Credential(
        kind="converter",
        label=f"문서 변환기 ({name})",
        health=LinkHealth.OK if choice.use_real else LinkHealth.NOT_CONFIGURED,
        detail=detail,
        missing_input=None if choice.use_real else "변환기 실행 경로",
    )


def _credentials(project_id: str, converter: tuple[str, str]) -> list[Credential]:
    return [
        _vault_credential(),
        Credential(
            kind="mail",
            label="하이웍스 메일 필터",
            health=LinkHealth.NOT_CONFIGURED,
            detail="계정과 API 접근 권한이 아직 없습니다.",
            missing_input="하이웍스 계정과 API 접근 권한",
        ),
        Credential(
            kind="vcs",
            label="깃허브 리포",
            health=LinkHealth.NOT_CONFIGURED,
            detail="개인 액세스 토큰이 아직 없습니다.",
            missing_input="개인 액세스 토큰과 대상 저장소",
        ),
        _converter_credential(converter),
        Credential(
            kind="llm",
            label="로컬 LLM 서버",
            health=LinkHealth.NOT_CONFIGURED,
            detail="사내 GPU 추론 서버 주소가 아직 없습니다.",
            missing_input="추론 서버 주소",
        ),
    ]


class FixtureIntegrationAdapter:
    def vcs_status(self, project_id: str) -> VcsStatus | None:
        return _VCS.get(project_id)

    def list_mismatches(self, project_id: str) -> list[Mismatch]:
        return [item for item in _MISMATCHES if item.project_id == project_id]

    def get_mismatch(self, mismatch_id: str) -> Mismatch | None:
        return next((item for item in _MISMATCHES if item.id == mismatch_id), None)

    def replace_mismatch(self, mismatch: Mismatch) -> Mismatch:
        for index, existing in enumerate(_MISMATCHES):
            if existing.id == mismatch.id:
                _MISMATCHES[index] = mismatch
                return mismatch
        _MISMATCHES.append(mismatch)
        return mismatch

    def list_mappings(self, project_id: str) -> list[TaskMapping]:
        return [mapping for owner, mapping in _MAPPINGS if owner == project_id]

    def resync_vcs(self, project_id: str) -> VcsStatus:
        current = _VCS[project_id]
        refreshed = replace(current, last_sync_at=datetime.now(tz=UTC))
        _VCS[project_id] = refreshed
        return refreshed

    def server(self) -> dict[str, object]:
        return dict(_SERVER[0])

    def list_models(self) -> list[ProjectModel]:
        return list(_MODELS)

    def replace_model(self, model: ProjectModel) -> ProjectModel:
        for index, existing in enumerate(_MODELS):
            if existing.project_id == model.project_id:
                _MODELS[index] = model
                return model
        _MODELS.append(model)
        return model

    def credentials(self, project_id: str, converter: tuple[str, str]) -> list[Credential]:
        return _credentials(project_id, converter)
