"""Ports for the documents module (ADR-018).

``DocumentConverterPort`` is the seam for kordoc, the one integration that already
exists. WP-PKD-030 drops the real adapter in behind this interface; it needs the
converter's install location and call style, which is still an open input.
"""

from __future__ import annotations

from typing import Protocol

from .entities import Document, DriveFile


class ConversionResult(Protocol):
    @property
    def succeeded(self) -> bool: ...

    @property
    def detail(self) -> str | None: ...


class DocumentConverterPort(Protocol):
    """Turns markdown into hwpx with a form template applied."""

    @property
    def name(self) -> str: ...

    @property
    def version(self) -> str: ...

    def convert(self, markdown: str, *, template: str) -> tuple[bool, str | None]:
        """Return ``(succeeded, failure_detail)``."""
        ...


class DocumentRepository(Protocol):
    def list_documents(self, project_id: str) -> list[Document]: ...

    def get_document(self, document_id: str) -> Document | None: ...

    def replace_document(self, document: Document) -> Document: ...

    def list_files(self, project_id: str) -> list[DriveFile]: ...

    def add_file(self, file: DriveFile) -> DriveFile: ...
