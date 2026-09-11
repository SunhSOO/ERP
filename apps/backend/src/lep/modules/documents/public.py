"""Stable public interface for the documents module."""

from __future__ import annotations

from functools import lru_cache

from sqlalchemy.orm import Session as DbSession

from ...common.adapters import converter_choice
from .application.services import DocumentService
from .domain.entities import MailAttachmentLinkInput, MailAttachmentLinkRef
from .domain.ports import DocumentConverterPort
from .infrastructure.fixtures import FixtureConverter, FixtureDocumentRepository
from .infrastructure.kordoc_converter import KordocConverter

__all__ = [
    "MailAttachmentLinkInput",
    "MailAttachmentLinkRef",
    "converter_status",
    "get_document_service",
    "register_mail_attachments",
]


def _converter() -> DocumentConverterPort:
    """Pick the converter per ADR-018. Default is the fixture."""

    return KordocConverter.from_env() if converter_choice().use_real else FixtureConverter()


@lru_cache(maxsize=1)
def get_document_service() -> DocumentService:
    return DocumentService(FixtureDocumentRepository(), _converter())


def converter_status() -> tuple[str, str]:
    """Converter name and version. Screen 09 lists it among the integrations."""

    service = get_document_service()
    return service.converter_name, service.converter_version


def register_mail_attachments(
    db: DbSession,
    *,
    project_id: str,
    mailbox_key: str,
    message_id: str,
    attachments: list[MailAttachmentLinkInput],
    actor_id: str,
) -> list[MailAttachmentLinkRef]:
    """Register approved mail attachments as drive references (ADR-021).

    Participates in the caller's transaction; never commits or rolls back the
    outer transaction. See ``docs/work-packages/2026-09-09-mail-approval.md``.
    """

    return get_document_service().register_mail_attachments(
        db,
        project_id=project_id,
        mailbox_key=mailbox_key,
        message_id=message_id,
        attachments=attachments,
        actor_id=actor_id,
    )
