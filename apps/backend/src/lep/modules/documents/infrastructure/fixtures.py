"""Empty document adapters.

Nothing is seeded. A new project has no documents in the conversion pipeline and
no files in the drive until someone puts them there.

The kordoc converter below is real: `documents/public.py` swaps it for
`KordocConverter` when `LEP_ADAPTER_CONVERTER=kordoc`, which is the default in
the container image.
"""

from __future__ import annotations

from ..domain.entities import Document, DriveFile


class UnavailableConverter:
    """변환기가 설정되지 않았을 때. 성공한 척하지 않는다."""

    @property
    def name(self) -> str:
        return "미설정"

    @property
    def version(self) -> str:
        return "알 수 없음"

    def convert(self, markdown: str, *, template: str) -> tuple[bool, str | None]:
        return False, "문서 변환기가 설정되지 않았습니다."


class EmptyDocumentRepository:
    def list_documents(self, project_id: str) -> list[Document]:
        return []

    def get_document(self, document_id: str) -> Document | None:
        return None

    def replace_document(self, document: Document) -> Document:
        return document

    def list_files(self, project_id: str) -> list[DriveFile]:
        return []

    def add_file(self, file: DriveFile) -> DriveFile:
        return file


FixtureConverter = UnavailableConverter
FixtureDocumentRepository = EmptyDocumentRepository
