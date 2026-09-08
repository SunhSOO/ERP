"""Obsidian vault adapter (WP-PKD-032, ADR-018).

An Obsidian vault is a folder of Markdown files, so this adapter is plain file
I/O: read the notes, parse ``[[wikilinks]]``, build the backlink index, and write
new notes as files a person can open in Obsidian itself.

**One folder per project.** The vault root holds a subfolder named after each
project's code, created when the project is created. Knowledge does not cross a
project boundary, and a note written for one project cannot appear in another's
screen.

The mockup's assumption is kept: editing happens in Obsidian, not here. This
screen shows sync state, the note list, and a read-only preview.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path

from ..domain.entities import Backlink, Note, NoteSource, SyncHealth, VaultStatus

WIKILINK = re.compile(r"\[\[([^\]|#]+)")
TASK_CODE = re.compile(r"\b(TSK-\d+|WP-[A-Z]+(?:-[A-Z]+)?-\d+)\b")

#: 옵시디언이 자기 상태를 두는 폴더. 노트로 취급하지 않는다.
IGNORED_DIRS = {".obsidian", ".trash", ".git"}

#: 폴더 이름으로 출처를 추정한다. 그 밖은 직접 작성으로 본다.
SOURCE_BY_DIR: dict[str, NoteSource] = {
    "meetings": NoteSource.MEETING,
    "회의록": NoteSource.MEETING,
    "inbox": NoteSource.MAIL,
    "메일": NoteSource.MAIL,
    "statements": NoteSource.STATEMENT,
    "과업지시서": NoteSource.STATEMENT,
}

#: 이 시간 넘게 아무것도 바뀌지 않았으면 동기화 지연으로 본다.
STALE_AFTER_HOURS = 12

#: 새 프로젝트 볼트에 만들어 두는 폴더. 옵시디언에서 바로 쓰기 좋게 한다.
STARTER_DIRS = ("meetings", "statements", "notes")


def vault_root() -> Path:
    return Path(os.getenv("LEP_OBSIDIAN_VAULT", ".vault"))


def slugify(value: str) -> str:
    return re.sub(r"[^0-9A-Za-z가-힣_-]+", "-", value).strip("-").lower() or "note"


@dataclass
class ObsidianVault:
    """Reads and writes a real Obsidian vault on disk, one folder per project."""

    root: Path

    @classmethod
    def from_env(cls) -> ObsidianVault:
        return cls(root=vault_root())

    # ── 프로젝트 폴더 ──────────────────────────────────────────────────────
    def project_dir(self, code: str) -> Path:
        return self.root / code

    def ensure(self, code: str) -> Path:
        """프로젝트 볼트를 만든다. 이미 있으면 그대로 둔다.

        사람이 이미 넣어 둔 노트를 건드리지 않도록 덮어쓰지 않는다.
        """

        base = self.project_dir(code)
        base.mkdir(parents=True, exist_ok=True)
        for name in STARTER_DIRS:
            (base / name).mkdir(exist_ok=True)

        readme = base / "README.md"
        if not readme.exists():
            readme.write_text(
                f"# {code}\n\n"
                "이 폴더는 프로젝트 볼트입니다. 옵시디언에서 열어 편집하세요.\n\n"
                "- `meetings/` 회의록\n"
                "- `statements/` 과업지시서에서 나온 노트\n"
                "- `notes/` 그 밖의 메모\n",
                encoding="utf-8",
            )
        return base

    # ── 읽기 ───────────────────────────────────────────────────────────────
    def _markdown_files(self, code: str) -> list[Path]:
        base = self.project_dir(code)
        if not base.is_dir():
            return []
        return sorted(
            p
            for p in base.rglob("*.md")
            if not any(part in IGNORED_DIRS for part in p.relative_to(base).parts)
        )

    def _note_id(self, path: Path, code: str) -> str:
        relative = path.relative_to(self.project_dir(code)).with_suffix("")
        return slugify("-".join(relative.parts))

    def _source_for(self, path: Path, code: str) -> NoteSource:
        parts = path.relative_to(self.project_dir(code)).parts
        for part in parts[:-1]:
            mapped = SOURCE_BY_DIR.get(part.lower())
            if mapped is not None:
                return mapped
        return NoteSource.MANUAL

    def status(self, project_id: str, code: str) -> VaultStatus:
        base = self.project_dir(code)
        if not base.is_dir():
            return VaultStatus(
                project_id=project_id,
                health=SyncHealth.FAILED,
                last_sync_at=datetime.now(tz=UTC),
                note_count=0,
                vault_path=str(base),
            )

        files = self._markdown_files(code)
        newest = max(
            (datetime.fromtimestamp(p.stat().st_mtime, tz=UTC) for p in files),
            default=datetime.now(tz=UTC),
        )
        hours = (datetime.now(tz=UTC) - newest).total_seconds() / 3600
        return VaultStatus(
            project_id=project_id,
            health=SyncHealth.STALE if hours > STALE_AFTER_HOURS else SyncHealth.OK,
            last_sync_at=newest,
            note_count=len(files),
            vault_path=str(base),
        )

    def list_notes(self, project_id: str, code: str) -> list[Note]:
        files = self._markdown_files(code)
        bodies: dict[Path, str] = {}
        for path in files:
            try:
                bodies[path] = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue

        stems = {p.stem: p for p in bodies}
        incoming: dict[Path, list[Backlink]] = {p: [] for p in bodies}
        for source_path, content in bodies.items():
            for match in WIKILINK.finditer(content):
                target = stems.get(match.group(1).strip())
                if target is not None and target != source_path:
                    incoming[target].append(
                        Backlink(
                            target=self._note_id(source_path, code),
                            label=source_path.stem,
                        )
                    )

        notes: list[Note] = []
        for path, content in bodies.items():
            codes = TASK_CODE.findall(content) or TASK_CODE.findall(path.stem)
            notes.append(
                Note(
                    id=self._note_id(path, code),
                    project_id=project_id,
                    title=path.stem,
                    source=self._source_for(path, code),
                    note_count=1,
                    updated_at=datetime.fromtimestamp(path.stat().st_mtime, tz=UTC).date(),
                    body=content,
                    backlinks=incoming[path],
                    warning="미확정 태그" if "#미확정" in content else None,
                    task_code=codes[0] if codes else None,
                )
            )
        notes.sort(key=lambda n: (n.updated_at or date.min), reverse=True)
        return notes

    def get_note(self, project_id: str, code: str, note_id: str) -> Note | None:
        return next((n for n in self.list_notes(project_id, code) if n.id == note_id), None)

    # ── 쓰기 ───────────────────────────────────────────────────────────────
    def create_note(self, code: str, *, title: str, body: str, folder: str = "notes") -> str:
        """새 노트를 파일로 쓴다. 기존 파일을 덮지 않는다.

        볼트는 사용자의 것이다. 같은 이름이 있으면 옆에 쓴다.
        """

        base = self.ensure(code) / folder
        base.mkdir(parents=True, exist_ok=True)
        safe = slugify(title)
        target = base / f"{title}.md"
        if target.exists():
            target = base / f"{title}-{safe[:8]}.md"
            suffix = 2
            while target.exists():
                target = base / f"{title}-{safe[:8]}-{suffix}.md"
                suffix += 1
        target.write_text(body, encoding="utf-8")
        return target.stem

    def resync(self, project_id: str, code: str) -> VaultStatus:
        """폴더를 다시 읽는다. 볼트는 로컬 파일이라 당겨올 원격이 없다."""

        return self.status(project_id, code)
