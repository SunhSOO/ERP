"""Stable public interface for the documents module."""

from __future__ import annotations

from functools import lru_cache

from ...common.adapters import converter_choice
from .application.services import DocumentService
from .domain.ports import DocumentConverterPort
from .infrastructure.fixtures import FixtureConverter, FixtureDocumentRepository
from .infrastructure.kordoc_converter import KordocConverter

__all__ = ["converter_status", "get_document_service"]


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
