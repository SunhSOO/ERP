"""Document pipeline and drive use cases."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime

from ....common.problems import not_found, state_conflict
from ...projects.public import require_project
from ..domain.entities import (
    Document,
    DriveCategory,
    DriveCategorySummary,
    DriveFile,
    PipelineStage,
    PipelineState,
)
from ..domain.ports import DocumentConverterPort, DocumentRepository

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

    def list_documents(self, project_id: str) -> list[Document]:
        require_project(project_id)
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
        self, project_id: str, category: DriveCategory | None = None
    ) -> list[DriveFile]:
        require_project(project_id)
        files = self._repository.list_files(project_id)
        if category is None:
            return files
        return [item for item in files if item.category is category]

    def drive_summary(self, project_id: str) -> list[DriveCategorySummary]:
        require_project(project_id)
        files = self._repository.list_files(project_id)
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

    def add_file(self, project_id: str, *, file_id: str, name: str, category: DriveCategory,
                 origin: str, size_bytes: int) -> DriveFile:
        """Add a file to the drive.

        원본문서 is read-only: a new version belongs in 산출문서 rather than
        replacing the customer's original. The rule lives here, not in the UI.
        """

        require_project(project_id)
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
