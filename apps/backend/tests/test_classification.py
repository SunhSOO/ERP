"""Classifying statement sections.

The rule the tests defend: a classifier that cannot answer must say so. It may
never leave a plausible-looking label behind, because the promote-to-task guard
and the reviewer both read that label as if something stood behind it.
"""

from __future__ import annotations

import json
from typing import Any

import pytest

from lep.modules.delivery.domain.entities import Confidence
from lep.modules.delivery.domain.ports import Category, Classification, SectionInput
from lep.modules.delivery.infrastructure.llm_classifier import (
    FixtureClassifier,
    _read_answer,
)

STATEMENT = """1.과업의 개요

1.1과업명

O정수장 데이터 전처리 및 AI 개발 용역

2.과업수행 일반사항

2.1 보안사항

O산출물은 외부로 반출하지 않는다
"""


def _answer(**fields: Any) -> dict[str, Any]:
    """모델 응답 봉투를 흉내 낸다."""

    return {"choices": [{"message": {"content": json.dumps(fields, ensure_ascii=False)}}]}


# ── 응답 해석 ─────────────────────────────────────────────────────────────


def test_a_well_formed_answer_is_accepted() -> None:
    result = _read_answer(
        "2.1",
        _answer(category="보안", actionable=False, confidence="high", reason="반출 제한"),
    )

    assert result.category is Category.SECURITY
    assert result.actionable is False
    assert result.confidence is Confidence.HIGH
    assert result.reason == "반출 제한"


def test_a_category_outside_the_allowed_set_is_refused() -> None:
    """모델이 새 카테고리를 지어내면 받지 않는다.

    받아 주면 화면에 우리가 정의한 적 없는 이름이 뜨고, 그 이름으로 필터를
    걸어도 아무것도 걸리지 않는다.
    """

    result = _read_answer(
        "1.1", _answer(category="기타등등", actionable=True, confidence="high")
    )

    assert result.category is Category.UNCLASSIFIED
    assert result.confidence is Confidence.LOW
    assert "기타등등" in result.reason


def test_an_unparseable_answer_becomes_unclassified() -> None:
    body: dict[str, Any] = {
        "choices": [{"message": {"content": "카테고리는 보안입니다."}}]
    }

    result = _read_answer("2.1", body)

    assert result.category is Category.UNCLASSIFIED
    assert "JSON" in result.reason


def test_a_missing_confidence_is_refused() -> None:
    result = _read_answer("1.1", _answer(category="과업범위", actionable=True))

    assert result.category is Category.UNCLASSIFIED


def test_a_non_boolean_actionable_is_refused() -> None:
    """`"true"`는 참이 아니다. 문자열을 참으로 읽으면 늘 참이 된다."""

    result = _read_answer(
        "1.1", _answer(category="과업범위", actionable="true", confidence="high")
    )

    assert result.category is Category.UNCLASSIFIED
    assert "actionable" in result.reason


def test_an_empty_response_envelope_becomes_unclassified() -> None:
    assert _read_answer("1.1", {}).category is Category.UNCLASSIFIED


# ── 픽스처 ────────────────────────────────────────────────────────────────


def test_the_fixture_classifier_classifies_nothing_and_says_so() -> None:
    results = FixtureClassifier().classify(
        [SectionInput(number="1.1", title="과업명", body="본문")]
    )

    assert results[0].category is Category.UNCLASSIFIED
    assert "설정되지 않아" in results[0].reason


# ── 엔드포인트 ────────────────────────────────────────────────────────────


def _upload(client: Any, project: dict[str, Any]) -> dict[str, Any]:
    response = client.post(
        f"/api/v1/projects/{project['id']}/statements",
        files={"file": ("과업지시서.md", STATEMENT.encode("utf-8"), "text/markdown")},
    )
    assert response.status_code == 201, response.text
    return dict(response.json()["data"])


def test_uploading_does_not_classify(client: Any, project: dict[str, Any]) -> None:
    """쪼개는 것과 분류하는 것은 다른 일이고 다른 시점에 일어난다."""

    statement = _upload(client, project)

    assert statement["clause_count"] == 4
    assert statement["classified_count"] == 0


def test_classifying_without_a_model_reports_that_nothing_happened(
    client: Any, project: dict[str, Any]
) -> None:
    """로컬 LLM이 없으면 없다고 말한다. 완료했다고 하지 않는다."""

    statement = _upload(client, project)

    run = client.post(f"/api/v1/statements/{statement['id']}/classify").json()["data"]

    assert run["classifier"] == "fixture"
    assert run["classified"] == 0
    assert run["failed"] == run["total"]


def test_a_failed_classification_leaves_the_reason_on_the_clause(
    client: Any, project: dict[str, Any]
) -> None:
    """검토하는 사람이 왜 미분류인지 화면에서 읽을 수 있어야 한다."""

    statement = _upload(client, project)
    client.post(f"/api/v1/statements/{statement['id']}/classify")

    clauses = client.get(f"/api/v1/statements/{statement['id']}/clauses").json()["data"]

    assert all(c["category"] == "미분류" for c in clauses)
    assert all(c["classified_reason"] for c in clauses)
    assert all(c["classified_by"] == "fixture" for c in clauses)


def test_classification_asks_the_model_and_stores_what_it_said(
    client: Any, project: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    """모델이 답하면 그 답이 조항에 남는다."""

    statement = _upload(client, project)

    def fake_build() -> tuple[Any, str | None]:
        class Stub:
            name = "stub-model"

            def classify(self, sections: list[SectionInput]) -> list[Classification]:
                return [
                    Classification(
                        number=s.number,
                        category=Category.SECURITY
                        if "보안" in s.title
                        else Category.SCOPE,
                        actionable="보안" not in s.title,
                        confidence=Confidence.HIGH,
                        reason="시험용 판단",
                    )
                    for s in sections
                ]

        return Stub(), None

    monkeypatch.setattr(
        "lep.modules.delivery.application.services.build_classifier", fake_build
    )

    run = client.post(f"/api/v1/statements/{statement['id']}/classify").json()["data"]
    assert run["classifier"] == "stub-model"
    assert run["classified"] == 4
    assert run["failed"] == 0

    clauses = client.get(f"/api/v1/statements/{statement['id']}/clauses").json()["data"]
    by_number = {c["article"]: c for c in clauses}
    assert by_number["2.1"]["category"] == "보안"
    assert by_number["2.1"]["actionable"] is False
    assert by_number["1.1"]["category"] == "과업범위"
    assert by_number["1.1"]["actionable"] is True

    # 문서의 집계도 함께 올라간다.
    listed = client.get(f"/api/v1/projects/{project['id']}/statements").json()["data"]
    assert listed[0]["classified_count"] == 4


def test_reclassifying_does_not_overwrite_a_reviewed_clause(
    client: Any, project: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    """사람이 고쳐 놓은 값을 재분류가 되돌리면 검토한 보람이 없다."""

    statement = _upload(client, project)

    calls: list[int] = []

    def fake_build() -> tuple[Any, str | None]:
        class Stub:
            name = "stub-model"

            def classify(self, sections: list[SectionInput]) -> list[Classification]:
                calls.append(len(sections))
                return [
                    Classification(
                        number=s.number,
                        category=Category.SCOPE,
                        actionable=True,
                        confidence=Confidence.HIGH,
                        reason="",
                    )
                    for s in sections
                ]

        return Stub(), None

    monkeypatch.setattr(
        "lep.modules.delivery.application.services.build_classifier", fake_build
    )

    client.post(f"/api/v1/statements/{statement['id']}/classify")
    client.post(f"/api/v1/statements/{statement['id']}/classify")

    # 두 번째 호출에는 넘길 절이 남아 있지 않다.
    assert calls == [4]


def test_classifying_an_unknown_statement_is_a_404(
    client: Any, signed_up: dict[str, str]
) -> None:
    response = client.post("/api/v1/statements/does-not-exist/classify")

    assert response.status_code == 404


def test_classification_requires_a_session(client: Any, project: dict[str, Any]) -> None:
    statement = _upload(client, project)
    client.post("/api/v1/auth/logout")

    response = client.post(f"/api/v1/statements/{statement['id']}/classify")

    assert response.status_code == 401
