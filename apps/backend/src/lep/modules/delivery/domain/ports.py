"""Ports the delivery module depends on but does not implement.

ADR-018. The domain names what it needs; infrastructure supplies it. Nothing
here imports a driver, a client, or a model.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from .entities import Confidence


class Category(StrEnum):
    """What a section of a statement of work is about.

    A closed set on purpose. A classifier that may return any string cannot be
    checked, and an unchecked label is worse than none — it looks like knowledge
    while carrying no guarantee. Anything outside this set is rejected and the
    section stays 미분류.
    """

    #: 수급인이 실제로 만들어 내야 하는 일. WBS 태스크가 되는 후보다.
    SCOPE = "과업범위"
    #: 제출해야 하는 산출물.
    DELIVERABLE = "산출물"
    #: 기간, 착수일, 검수 일정.
    SCHEDULE = "일정"
    #: 보안, 개인정보, 반출 제한.
    SECURITY = "보안"
    #: 품질 기준, 성능 요건, 검수 조건.
    QUALITY = "품질"
    #: 계약 조건, 하도급, 하자보수, 위반 시 조치.
    CONTRACT = "계약조건"
    #: 위 어디에도 들지 않는 설명이나 배경.
    GENERAL = "일반사항"
    #: 분류하지 못했다. 모델이 답하지 않았거나 답이 규칙을 벗어났다.
    UNCLASSIFIED = "미분류"


@dataclass(frozen=True, slots=True)
class SectionInput:
    """분류할 절 하나. 문서 형식과 무관한 형태로 넘긴다."""

    number: str
    title: str
    body: str


@dataclass(frozen=True, slots=True)
class Classification:
    """절 하나에 대한 판단.

    실패를 성공으로 숨기지 않는다. 모델이 답하지 못했으면 ``미분류``에
    ``낮음``으로 돌아오고 ``reason``이 왜인지 말한다.
    """

    number: str
    category: Category
    #: WBS 태스크가 될 수 있는 일인지. 계약 조건은 참이 아니다.
    actionable: bool
    confidence: Confidence
    #: 그렇게 판단한 근거 한 줄. 사람이 검토할 때 읽는다.
    reason: str = ""

    @classmethod
    def unclassified(cls, number: str, reason: str) -> Classification:
        return cls(
            number=number,
            category=Category.UNCLASSIFIED,
            actionable=False,
            confidence=Confidence.LOW,
            reason=reason,
        )


class ClauseClassifier(Protocol):
    """과업지시서의 절을 분류한다.

    구현은 두 가지다. 픽스처는 아무것도 분류하지 않고 그 사실을 말한다. 실제
    구현은 로컬 LLM에 묻는다. 어느 쪽인지는 설정이 정하고, 화면은 언제나
    어느 쪽이 답했는지 알 수 있다.
    """

    @property
    def name(self) -> str:
        """화면에 보여 줄 분류기 이름."""
        ...

    def classify(self, sections: list[SectionInput]) -> list[Classification]:
        """주어진 절들을 분류한다. 입력과 같은 길이의 목록을 돌려준다."""
        ...
