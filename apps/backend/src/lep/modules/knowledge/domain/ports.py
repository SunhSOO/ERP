"""Ports for the knowledge module (ADR-018).

``VaultPort`` is the seam the real Obsidian adapter drops into at WP-PKD-032. The
vault is local files, so the real adapter reads and writes markdown; the fixture
adapter keeps the same shapes in memory.
"""

from __future__ import annotations

from typing import Protocol

from .entities import ActionItem, Decision, Meeting, Note, VaultStatus


class VaultPort(Protocol):
    """The knowledge vault, whatever backs it."""

    def status(self, project_id: str) -> VaultStatus | None: ...

    def list_notes(self, project_id: str) -> list[Note]: ...

    def get_note(self, note_id: str) -> Note | None: ...

    def create_note(self, note: Note) -> Note: ...

    def resync(self, project_id: str) -> VaultStatus: ...


class MeetingRepository(Protocol):
    def list_meetings(self, project_id: str) -> list[Meeting]: ...

    def get_meeting(self, meeting_id: str) -> Meeting | None: ...

    def replace_meeting(self, meeting: Meeting) -> Meeting: ...

    def list_decisions(self, meeting_id: str) -> list[Decision]: ...

    def replace_decision(self, decision: Decision) -> Decision: ...

    def list_action_items(self, meeting_id: str) -> list[ActionItem]: ...
