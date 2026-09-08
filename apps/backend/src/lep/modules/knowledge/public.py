"""Stable public interface for the knowledge module.

Projects asks for a vault folder when a project is created. Mail asks for a note
to be written. Neither touches the filesystem itself.
"""

from __future__ import annotations

from functools import lru_cache

from .infrastructure.obsidian_vault import ObsidianVault

__all__ = [
    "create_note_from",
    "ensure_project_vault",
    "get_vault",
    "project_vault_summary",
]


@lru_cache(maxsize=1)
def get_vault() -> ObsidianVault:
    return ObsidianVault.from_env()


def ensure_project_vault(project_id: str, code: str) -> str:
    """프로젝트 볼트 폴더를 만든다. 프로젝트를 만들 때 호출된다.

    실패해도 프로젝트 생성 자체를 막지 않는다. 볼트는 나중에 다시 만들 수 있고,
    화면 09가 볼트 상태를 그대로 보여 준다.
    """

    try:
        return str(get_vault().ensure(code))
    except OSError:
        return ""


def project_vault_summary(project_id: str, code: str) -> tuple[str, str]:
    """홈 카드에 쓸 ``(health, note)``."""

    status = get_vault().status(project_id, code)
    note = {
        "ok": f"노트 {status.note_count}개",
        "stale": f"노트 {status.note_count}개 · 최근 변경 없음",
        "failed": "볼트 폴더 없음",
    }[status.health.value]
    # 볼트의 SyncHealth와 프로젝트 카드의 SyncHealth는 값 집합이 다르다.
    # failed는 카드에서 mismatch로 보여 준다.
    health = {"ok": "ok", "stale": "stale", "failed": "mismatch"}[status.health.value]
    return health, note


def create_note_from(
    code: str, *, title: str, body: str, folder: str = "notes"
) -> str:
    """다른 모듈을 대신해 볼트에 노트를 만든다."""

    return get_vault().create_note(code, title=title, body=body, folder=folder)
