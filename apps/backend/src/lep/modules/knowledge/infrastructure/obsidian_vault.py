"""Obsidian vault adapter (WP-PKD-032, ADR-018).

An Obsidian vault is a folder of Markdown files, so this adapter is plain file
I/O: read the notes, parse ``[[wikilinks]]``, build the backlink index, and write
new notes as files the user can open in Obsidian itself.

The mockup's assumption is kept: editing happens in Obsidian, not here. This
screen shows sync state, the note list, and a read-only preview.

Notes are scoped to a project by folder. ``LEP_OBSIDIAN_PROJECT_DIRS`` maps a
project ID to a subfolder; without a mapping the whole vault is one project's.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path

from ..domain.entities import Backlink, Note, NoteSource, SyncHealth, VaultStatus

WIKILINK = re.compile(r"\[\[([^\]|#]+)")
TASK_CODE = re.compile(r"\b(TSK-\d+|WP-[A-Z]+(?:-[A-Z]+)?-\d+)\b")

#: Folder names Obsidian uses for its own state; never treated as notes.
IGNORED_DIRS = {".obsidian", ".trash", ".git"}

#: Folder name to note source. Anything else is treated as hand-written.
SOURCE_BY_DIR: dict[str, NoteSource] = {
    "meetings": NoteSource.MEETING,
    "inbox": NoteSource.MAIL,
    "tasks": NoteSource.STATEMENT,
}

#: A vault not synced within this many hours is reported as stale rather than
#: silently shown as current.
STALE_AFTER_HOURS = 12


def project_dirs() -> dict[str, str]:
    raw = os.getenv("LEP_OBSIDIAN_PROJECT_DIRS")
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return {str(k): str(v) for k, v in parsed.items()} if isinstance(parsed, dict) else {}


def slugify(value: str) -> str:
    return re.sub(r"[^0-9A-Za-z가-힣_-]+", "-", value).strip("-").lower() or "note"


@dataclass
class ObsidianVault:
    """Reads and writes a real Obsidian vault on disk."""

    root: Path
    scopes: dict[str, str]
    #: Set when the last read failed, so the screen can say so honestly.
    _last_error: str | None = None

    @classmethod
    def from_env(cls, root: str) -> ObsidianVault:
        return cls(root=Path(root), scopes=project_dirs())

    # ── helpers ────────────────────────────────────────────────────────────
    def _scope(self, project_id: str) -> Path:
        subdir = self.scopes.get(project_id)
        return self.root / subdir if subdir else self.root

    def _markdown_files(self, project_id: str) -> list[Path]:
        base = self._scope(project_id)
        if not base.is_dir():
            return []
        return sorted(
            path
            for path in base.rglob("*.md")
            if not any(part in IGNORED_DIRS for part in path.relative_to(base).parts)
        )

    def _note_id(self, path: Path, project_id: str) -> str:
        relative = path.relative_to(self._scope(project_id)).with_suffix("")
        return slugify("-".join(relative.parts))

    def _source_for(self, path: Path, project_id: str) -> NoteSource:
        parts = path.relative_to(self._scope(project_id)).parts
        for part in parts[:-1]:
            mapped = SOURCE_BY_DIR.get(part.lower())
            if mapped is not None:
                return mapped
        return NoteSource.MANUAL

    def _read(self, path: Path) -> str | None:
        try:
            return path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return None

    # ── VaultPort ──────────────────────────────────────────────────────────
    def status(self, project_id: str) -> VaultStatus | None:
        base = self._scope(project_id)
        if not base.is_dir():
            return VaultStatus(
                project_id=project_id,
                health=SyncHealth.FAILED,
                last_sync_at=datetime.now(tz=UTC),
                note_count=0,
                vault_path=str(base),
            )

        files = self._markdown_files(project_id)
        newest = max(
            (datetime.fromtimestamp(path.stat().st_mtime, tz=UTC) for path in files),
            default=datetime.now(tz=UTC),
        )
        age_hours = (datetime.now(tz=UTC) - newest).total_seconds() / 3600
        health = SyncHealth.STALE if age_hours > STALE_AFTER_HOURS else SyncHealth.OK

        return VaultStatus(
            project_id=project_id,
            health=SyncHealth.FAILED if self._last_error else health,
            last_sync_at=newest,
            note_count=len(files),
            vault_path=str(base),
        )

    def list_notes(self, project_id: str) -> list[Note]:
        files = self._markdown_files(project_id)
        # One pass to collect titles, a second to resolve links into backlinks.
        bodies: dict[Path, str] = {}
        for path in files:
            content = self._read(path)
            if content is not None:
                bodies[path] = content

        stems = {path.stem: path for path in bodies}
        incoming: dict[Path, list[Backlink]] = {path: [] for path in bodies}

        for source_path, content in bodies.items():
            for match in WIKILINK.finditer(content):
                target = match.group(1).strip()
                target_path = stems.get(target)
                if target_path is not None and target_path != source_path:
                    incoming[target_path].append(
                        Backlink(
                            target=self._note_id(source_path, project_id),
                            label=source_path.stem,
                        )
                    )

        notes: list[Note] = []
        for path, content in bodies.items():
            codes = TASK_CODE.findall(content) or TASK_CODE.findall(path.stem)
            modified = datetime.fromtimestamp(path.stat().st_mtime, tz=UTC).date()
            notes.append(
                Note(
                    id=self._note_id(path, project_id),
                    project_id=project_id,
                    title=path.stem,
                    source=self._source_for(path, project_id),
                    note_count=1,
                    updated_at=modified,
                    body=content,
                    backlinks=incoming[path],
                    warning="미확정 태그" if "#미확정" in content else None,
                    task_code=codes[0] if codes else None,
                )
            )

        notes.sort(key=lambda note: (note.updated_at or date.min), reverse=True)
        return notes

    def get_note(self, note_id: str) -> Note | None:
        for project_id in self.scopes or {"*": ""}:
            for note in self.list_notes(project_id):
                if note.id == note_id:
                    return note
        return None

    def create_note(self, note: Note) -> Note:
        """Write a new note as a file Obsidian will pick up.

        Never overwrites. A collision means someone already wrote that note and
        losing their text would be worse than failing the request.
        """

        base = self._scope(note.project_id)
        target = base / f"{note.title or note.id}.md"
        try:
            base.mkdir(parents=True, exist_ok=True)
            if target.exists():
                target = base / f"{note.title or note.id}-{note.id}.md"
            target.write_text(note.body, encoding="utf-8")
        except OSError as exc:
            self._last_error = str(exc)
            raise
        return note

    def resync(self, project_id: str) -> VaultStatus:
        """Re-read the folder. There is nothing to pull; the vault is local files."""

        self._last_error = None
        status = self.status(project_id)
        if status is None:
            raise ValueError(f"볼트 경로를 찾을 수 없습니다: {project_id}")
        return status
