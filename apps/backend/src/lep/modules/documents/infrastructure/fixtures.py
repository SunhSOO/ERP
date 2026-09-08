"""Fixture document adapters (ADR-018).

목업 데이터다. 실제 고객·직원 정보가 아니다. AGENTS.md 1절 7항.
"""

from __future__ import annotations

from datetime import UTC, date, datetime

from ..domain.entities import (
    Document,
    DriveCategory,
    DriveFile,
    PipelineStage,
    PipelineState,
)

PRJ_DAON = "prj-daon"

_MARKDOWN = """# 검수 결과 보고서

## 1. 개요

09월 검수 대상: WMS 연동 모듈

## 2. 결과

| 항목 | 결과 |
|---|---|
| 인터페이스 정의 | 조건부 통과 |
| 성능 테스트 | 통과 |
"""

_DOCUMENTS: list[Document] = [
    Document(
        id="doc-inspection-09",
        project_id=PRJ_DAON,
        title="검수 결과 보고서_09월",
        stage=PipelineStage.GENERATING,
        state=PipelineState.RUNNING,
        converter="kordoc",
        author="김서준",
        updated_at=datetime(2026, 9, 6, 0, 10, tzinfo=UTC),
        markdown=_MARKDOWN,
    ),
    Document(
        id="doc-monthly-08",
        project_id=PRJ_DAON,
        title="월간 진행 보고서_08월",
        stage=PipelineStage.SENT,
        state=PipelineState.DONE,
        converter="kordoc",
        author="김서준",
        updated_at=datetime(2026, 8, 31, 9, 0, tzinfo=UTC),
        markdown="# 월간 진행 보고서\n",
    ),
    Document(
        id="doc-change-request",
        project_id=PRJ_DAON,
        title="변경계약 요청서",
        stage=PipelineStage.GENERATING,
        state=PipelineState.FAILED,
        converter="kordoc",
        author="박도윤",
        updated_at=datetime(2026, 9, 5, 2, 0, tzinfo=UTC),
        markdown="# 변경계약 요청서\n",
        failure_reason="표 병합 셀을 변환하지 못했습니다.",
    ),
]

_FILES: list[DriveFile] = [
    DriveFile(
        id="file-contract",
        project_id=PRJ_DAON,
        name="계약서_원본_2026-03-02.pdf",
        category=DriveCategory.ORIGINAL,
        origin="계약 모듈",
        size_bytes=1_800_000,
        modified=date(2026, 3, 2),
    ),
    DriveFile(
        id="file-statement",
        project_id=PRJ_DAON,
        name="과업지시서_다온물산_v1.hwpx",
        category=DriveCategory.ORIGINAL,
        origin="지식화됨",
        size_bytes=640_000,
        modified=date(2026, 3, 2),
    ),
    DriveFile(
        id="file-wms-spec",
        project_id=PRJ_DAON,
        name="WMS_스펙.pdf",
        category=DriveCategory.ORIGINAL,
        origin="메일 첨부 (고객 제공)",
        size_bytes=3_100_000,
        modified=date(2026, 8, 14),
    ),
    DriveFile(
        id="file-change-request",
        project_id=PRJ_DAON,
        name="변경계약_요청서_v1.docx",
        category=DriveCategory.ORIGINAL,
        origin="메일 첨부",
        size_bytes=220_000,
        modified=date(2026, 9, 5),
        warning="미분류",
    ),
    DriveFile(
        id="file-requirements",
        project_id=PRJ_DAON,
        name="요구사항_초안_이메일첨부.pdf",
        category=DriveCategory.ORIGINAL,
        origin="메일 첨부",
        size_bytes=900_000,
        modified=date(2026, 3, 4),
    ),
    DriveFile(
        id="file-monthly-08",
        project_id=PRJ_DAON,
        name="월간 진행 보고서_08월.hwpx",
        category=DriveCategory.REPORT,
        origin="문서 변환",
        size_bytes=410_000,
        modified=date(2026, 8, 31),
    ),
    DriveFile(
        id="file-if-spec-v2",
        project_id=PRJ_DAON,
        name="인터페이스 정의서 v2.1.hwpx",
        category=DriveCategory.DELIVERABLE,
        origin="산출물",
        size_bytes=1_200_000,
        modified=date(2026, 9, 6),
        warning="승인본과 다른 작업본",
    ),
]


class FixtureConverter:
    """Stands in for kordoc until WP-PKD-030."""

    @property
    def name(self) -> str:
        return "kordoc"

    @property
    def version(self) -> str:
        return "2.4.1"

    def convert(self, markdown: str, *, template: str) -> tuple[bool, str | None]:
        # The fixture never actually converts. It reports honestly rather than
        # claiming a success that did not happen. AGENTS.md 19절.
        if not markdown.strip():
            return False, "빈 문서는 변환할 수 없습니다."
        return True, None


class FixtureDocumentRepository:
    def list_documents(self, project_id: str) -> list[Document]:
        return [item for item in _DOCUMENTS if item.project_id == project_id]

    def get_document(self, document_id: str) -> Document | None:
        return next((item for item in _DOCUMENTS if item.id == document_id), None)

    def replace_document(self, document: Document) -> Document:
        for index, existing in enumerate(_DOCUMENTS):
            if existing.id == document.id:
                _DOCUMENTS[index] = document
                return document
        _DOCUMENTS.append(document)
        return document

    def list_files(self, project_id: str) -> list[DriveFile]:
        return [item for item in _FILES if item.project_id == project_id]

    def add_file(self, file: DriveFile) -> DriveFile:
        _FILES.append(file)
        return file
