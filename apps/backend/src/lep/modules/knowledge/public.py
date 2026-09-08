"""Stable public interface for the knowledge module.

Screen 06 turns a mail message into a vault note. It does that through
:func:`create_note_from`, never by writing knowledge's storage itself.
"""

from __future__ import annotations

from functools import lru_cache

from ...common.adapters import vault_choice, vault_root
from .application.services import KnowledgeService
from .domain.entities import NoteSource
from .domain.ports import VaultPort
from .infrastructure.fixture_vault import FixtureMeetingRepository, FixtureVault
from .infrastructure.obsidian_vault import ObsidianVault

__all__ = ["create_note_from", "get_knowledge_service", "vault_note_count"]


def _vault() -> VaultPort:
    """Pick the vault per ADR-018. Default is the fixture."""

    root = vault_root()
    if vault_choice().use_real and root is not None:
        return ObsidianVault.from_env(root)
    return FixtureVault()


@lru_cache(maxsize=1)
def get_knowledge_service() -> KnowledgeService:
    # Meetings stay on the fixture. The vault is files on disk; meeting records
    # are not, and they get a real store in WP-PKD-020.
    return KnowledgeService(_vault(), FixtureMeetingRepository())


def create_note_from(
    project_id: str, *, note_id: str, title: str, body: str, source: str
) -> str:
    """Create a vault note on another module's behalf and return its ID."""

    note = get_knowledge_service().create_note(
        project_id,
        note_id=note_id,
        title=title,
        body=body,
        source=NoteSource(source),
    )
    return note.id


def vault_note_count(project_id: str) -> int:
    return get_knowledge_service().get_vault_status(project_id).note_count
