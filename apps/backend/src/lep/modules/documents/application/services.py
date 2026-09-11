"""Document pipeline and drive use cases."""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import replace
from datetime import UTC, datetime

from sqlalchemy.orm import Session as DbSession

from ....common.db import as_utc
from ....common.problems import ProblemError, not_found, state_conflict
from ...iam.public import User
from ...projects.public import get_project_service, require_project
from ..domain.entities import (
    Document,
    DriveCategory,
    DriveCategorySummary,
    DriveFile,
    MailAttachmentLinkInput,
    MailAttachmentLinkRef,
    PipelineStage,
    PipelineState,
)
from ..domain.ports import DocumentConverterPort, DocumentRepository
from ..infrastructure import mail_links

#: All four drive categories, including 원본문서, are permitted for an approved
#: mail attachment reference — unlike ``add_file``, which is a direct upload.
_ALLOWED_LINK_CATEGORIES = frozenset(category.value for category in DriveCategory)

_MESSAGE_ID_MAX = 255
_NAME_MAX = 255
_CONTENT_TYPE_MAX = 255
#: Sanity bound, not a real upload limit — mail attachments never approach this.
_MAX_SIZE_BYTES = 10 * 1024 * 1024 * 1024
#: ``part_index`` stays a 32-bit SQL ``INTEGER``; PostgreSQL would reject
#: anything past this at insert time with a far less clear error.
_SQL_INT32_MAX = 2_147_483_647
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_PATH_CHARS = frozenset({"/", "\\"})
#: RFC 7230 ``token``, doubled for ``type/subtype``. Excludes every control
#: character by construction, so a CRLF-bearing ``Content-Type`` never parses.
_MIME_TOKEN = r"[!#$%&'*+\-.^_`|~0-9A-Za-z]+"
_MIME_PATTERN = re.compile(rf"^{_MIME_TOKEN}/{_MIME_TOKEN}$")


def _has_control_chars(value: str) -> bool:
    return any(ord(ch) < 0x20 or ord(ch) == 0x7F for ch in value)


def _safe_filename(name: str) -> str:
    # Control characters (a bare CR/LF included) must be rejected on the raw
    # name: stripping first would silently swallow a leading/trailing CRLF
    # and let it through as if it had never been there.
    if _has_control_chars(name):
        raise ProblemError("VALIDATION_FAILED", "첨부 파일명에 제어 문자를 쓸 수 없습니다.")
    stripped = name.strip()
    if not stripped or len(stripped) > _NAME_MAX:
        raise ProblemError("VALIDATION_FAILED", "첨부 파일명이 올바르지 않습니다.")
    if stripped in {".", ".."} or any(ch in _PATH_CHARS for ch in stripped):
        raise ProblemError("VALIDATION_FAILED", "첨부 파일명에 경로 문자를 쓸 수 없습니다.")
    return stripped


def _opaque_identity(value: str, *, max_length: int, label: str) -> str:
    """A message id is an opaque identity the mail module owns. Trimming it
    here would let two distinct identities collide on the unique constraint;
    reject anything but an exact, well-formed value instead of normalising
    it."""

    if not value or len(value) > max_length:
        raise ProblemError("VALIDATION_FAILED", f"{label}가 올바르지 않습니다.")
    if _has_control_chars(value):
        raise ProblemError("VALIDATION_FAILED", f"{label}에 제어 문자를 쓸 수 없습니다.")
    if value != value.strip():
        raise ProblemError("VALIDATION_FAILED", f"{label} 앞뒤 공백은 허용되지 않습니다.")
    return value


def _mailbox_key(value: str) -> str:
    """ADR-021: a mailbox key is the SHA-256 hex digest of the mailbox
    identity, always exactly 64 lowercase hex characters. Rejected outright
    rather than normalised — an opaque identity that isn't already in the
    one true form is a caller bug, not something to coerce."""

    if not _SHA256_PATTERN.fullmatch(value):
        raise ProblemError("VALIDATION_FAILED", "mailbox_key가 올바르지 않습니다.")
    return value


_CATEGORY_META: dict[DriveCategory, tuple[str, str, bool]] = {
    DriveCategory.ORIGINAL: (
        "원본문서",
        "계약서·과업지시서·고객 원본 자료",
        True,
    ),
    DriveCategory.REPORT: ("보고문서", "주간·월간 보고, 회의록 발송본", False),
    DriveCategory.DELIVERABLE: ("산출문서", "검토·승인 대상 산출물", False),
    DriveCategory.SOURCE: ("소스코드", "깃허브 연동", False),
}


class DocumentService:
    def __init__(
        self, repository: DocumentRepository, converter: DocumentConverterPort
    ) -> None:
        self._repository = repository
        self._converter = converter

    @property
    def converter_name(self) -> str:
        return self._converter.name

    @property
    def converter_version(self) -> str:
        return self._converter.version

    def list_documents(self, db: DbSession, project_id: str) -> list[Document]:
        require_project(db, project_id)
        return self._repository.list_documents(project_id)

    def get_document(self, document_id: str) -> Document:
        document = self._repository.get_document(document_id)
        if document is None:
            raise not_found(f"문서를 찾을 수 없습니다: {document_id}")
        return document

    def convert(self, document_id: str, *, template: str = "표준 검수보고서") -> Document:
        """Run the conversion and record what actually happened.

        A failure is stored as a failure. The screen shows it with a retry action
        rather than pretending the document is ready.
        """

        document = self.get_document(document_id)
        if document.state is PipelineState.RUNNING and document.stage >= PipelineStage.REVIEW:
            raise state_conflict("이미 변환이 끝난 문서입니다.")

        succeeded, detail = self._converter.convert(document.markdown, template=template)
        updated = replace(
            document,
            stage=PipelineStage.REVIEW if succeeded else PipelineStage.GENERATING,
            state=PipelineState.DONE if succeeded else PipelineState.FAILED,
            failure_reason=None if succeeded else detail,
            updated_at=datetime.now(tz=UTC),
        )
        return self._repository.replace_document(updated)

    def retry(self, document_id: str) -> Document:
        document = self.get_document(document_id)
        if document.state is not PipelineState.FAILED:
            raise state_conflict("실패한 문서만 다시 시도할 수 있습니다.")
        return self.convert(document_id)

    def list_files(
        self,
        db: DbSession,
        project_id: str,
        category: DriveCategory | None = None,
        *,
        actor: User,
    ) -> list[DriveFile]:
        require_project(db, project_id)
        files = self._repository.list_files(project_id) + self._linked_files(
            db, project_id, actor
        )
        if category is None:
            return files
        return [item for item in files if item.category is category]

    def drive_summary(
        self, db: DbSession, project_id: str, *, actor: User
    ) -> list[DriveCategorySummary]:
        require_project(db, project_id)
        files = self._repository.list_files(project_id) + self._linked_files(
            db, project_id, actor
        )
        summaries: list[DriveCategorySummary] = []
        for category, (label, description, read_only) in _CATEGORY_META.items():
            in_category = [item for item in files if item.category is category]
            warnings = [item for item in in_category if item.warning]
            summaries.append(
                DriveCategorySummary(
                    category=category,
                    label=label,
                    description=description,
                    count=len(in_category),
                    read_only=read_only,
                    warning=(
                        f"승인본과 다른 작업본 {len(warnings)}건" if warnings else None
                    ),
                )
            )
        return summaries

    def add_file(self, db: DbSession, project_id: str, *, file_id: str, name: str,
                 category: DriveCategory, origin: str, size_bytes: int) -> DriveFile:
        """Add a file to the drive.

        원본문서 is read-only: a new version belongs in 산출문서 rather than
        replacing the customer's original. The rule lives here, not in the UI.
        """

        require_project(db, project_id)
        if category is DriveCategory.ORIGINAL:
            raise state_conflict(
                "원본문서는 읽기 전용입니다. 새 버전은 산출문서에 올려 주세요."
            )
        return self._repository.add_file(
            DriveFile(
                id=file_id,
                project_id=project_id,
                name=name,
                category=category,
                origin=origin,
                size_bytes=size_bytes,
                modified=datetime.now(tz=UTC).date(),
            )
        )

    # ── mail attachment links (ADR-021) ─────────────────────────────────────

    def register_mail_attachments(
        self,
        db: DbSession,
        *,
        project_id: str,
        mailbox_key: str,
        message_id: str,
        attachments: Sequence[MailAttachmentLinkInput],
        actor_id: str,
    ) -> list[MailAttachmentLinkRef]:
        """Register approved mail attachments as drive references.

        Participates in the caller's transaction: never commits, never rolls
        back the outer transaction. The whole batch is validated before any
        write, and ``mail_links.register`` isolates its own writes in a
        SAVEPOINT so a mid-batch conflict cannot leave a partial batch.
        """

        require_project(db, project_id)

        clean_mailbox_key = _mailbox_key(mailbox_key)
        clean_message_id = _opaque_identity(
            message_id, max_length=_MESSAGE_ID_MAX, label="message_id"
        )
        clean_actor_id = actor_id.strip()
        if not clean_actor_id:
            raise ProblemError("VALIDATION_FAILED", "actor_id가 필요합니다.")
        if not attachments:
            # A mail-only approval (no drive-worthy attachment) is a valid,
            # empty batch, not an error — the caller still gets a project and
            # identity check for its own decision record.
            return []

        seen_parts: set[int] = set()
        validated: list[MailAttachmentLinkInput] = []
        for item in attachments:
            if not isinstance(item.part_index, int) or isinstance(item.part_index, bool):
                raise ProblemError("VALIDATION_FAILED", "part_index는 정수여야 합니다.")
            if item.part_index < 0 or item.part_index > _SQL_INT32_MAX:
                raise ProblemError(
                    "VALIDATION_FAILED", "part_index는 0 이상, SQL int 범위 이내여야 합니다."
                )
            if item.part_index in seen_parts:
                raise ProblemError(
                    "VALIDATION_FAILED", f"중복된 첨부 part_index: {item.part_index}"
                )
            seen_parts.add(item.part_index)

            safe_name = _safe_filename(item.name)
            # Control characters (a bare CR/LF included) must be rejected on the
            # raw content_type: stripping first would silently swallow a
            # leading/trailing CRLF and let it through as if never there.
            if _has_control_chars(item.content_type):
                raise ProblemError(
                    "VALIDATION_FAILED", "content_type에 제어 문자를 쓸 수 없습니다."
                )
            content_type = item.content_type.strip()
            if len(content_type) > _CONTENT_TYPE_MAX or not _MIME_PATTERN.match(content_type):
                raise ProblemError("VALIDATION_FAILED", "content_type이 올바르지 않습니다.")
            if not isinstance(item.size_bytes, int) or isinstance(item.size_bytes, bool):
                raise ProblemError("VALIDATION_FAILED", "size_bytes는 정수여야 합니다.")
            if item.size_bytes < 0 or item.size_bytes > _MAX_SIZE_BYTES:
                raise ProblemError("VALIDATION_FAILED", "size_bytes가 올바르지 않습니다.")
            sha256 = item.sha256.strip().lower()
            if not _SHA256_PATTERN.fullmatch(sha256):
                raise ProblemError("VALIDATION_FAILED", "sha256이 올바르지 않습니다.")
            if item.category not in _ALLOWED_LINK_CATEGORIES:
                raise ProblemError(
                    "VALIDATION_FAILED", f"허용되지 않는 분류입니다: {item.category}"
                )

            validated.append(
                MailAttachmentLinkInput(
                    part_index=item.part_index,
                    name=safe_name,
                    content_type=content_type,
                    size_bytes=item.size_bytes,
                    sha256=sha256,
                    category=item.category,
                )
            )

        return mail_links.register(
            db,
            project_id=project_id,
            mailbox_key=clean_mailbox_key,
            message_id=clean_message_id,
            actor_id=clean_actor_id,
            attachments=validated,
        )

    def _can_view_links(self, db: DbSession, project_id: str, actor: User) -> bool:
        """Active admin, or the project's creator. No other actor sees a
        mail-linked reference or is counted toward its total."""

        if actor.status.value != "active":
            return False
        if actor.is_admin:
            return True
        project = get_project_service(db).get_project(project_id)
        return project.created_by == actor.id

    def _linked_files(self, db: DbSession, project_id: str, actor: User) -> list[DriveFile]:
        if not self._can_view_links(db, project_id, actor):
            return []
        return [
            DriveFile(
                id=row.id,
                project_id=row.project_id,
                name=row.name,
                category=DriveCategory(row.category),
                origin="메일 원본 연결",
                size_bytes=row.size_bytes,
                modified=as_utc(row.created_at).date(),
                warning=None,
                source_mail_id=row.message_id,
                source_part_index=row.part_index,
                source_kind="mail_attachment",
                sha256=row.sha256,
            )
            for row in mail_links.list_for_project(db, project_id)
        ]
