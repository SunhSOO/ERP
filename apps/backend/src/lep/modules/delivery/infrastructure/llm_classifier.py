"""Classifying statement sections with a local LLM (ADR-018).

The split matters. Cutting a document into sections is a **rule**: the decimal
numbering is exact, so the same document always yields the same sections and the
reason for every split can be pointed at. Deciding that 3.5 보안사항 is a security
constraint rather than a task is a **judgement**, and that is what the model is
for. Rules first, model only where rules cannot reach.

The model runs on the company's own GPU through ollama's OpenAI-compatible
endpoint. Statements of work are client documents under confidentiality; they do
not leave the building.

Nothing here invents a classification. If the model is unreachable, answers
outside the allowed set, or returns unparseable output, the section comes back
미분류 at low confidence with the reason attached. The promote-to-task guard
already refuses to act on low confidence, so a failure here costs a person some
manual review — never a wrong task silently entering the WBS.
"""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

from ....common.adapters import llm_base_url, llm_model, llm_timeout_seconds
from ..domain.entities import Confidence
from ..domain.ports import Category, Classification, ClauseClassifier, SectionInput

logger = logging.getLogger("lep.delivery.classifier")

#: 한 절에서 모델에 보내는 본문의 최대 길이.
#:
#: 과업 세부내용은 11,000자가 넘기도 한다. 전부 보내면 느려지기만 하고 분류가
#: 나아지지 않는다. 절이 무엇에 관한 것인지는 앞부분에서 이미 드러난다.
MAX_BODY_CHARS = 3000

#: 동시에 보낼 요청 수. ollama의 병렬 슬롯과 맞춘다.
CONCURRENCY = 4

_CONFIDENCE = {c.value: c for c in Confidence}
_CATEGORIES = {c.value: c for c in Category}

SYSTEM_PROMPT = """너는 한국 공공·민간 용역 과업지시서를 분류하는 도구다.

절 하나를 받아 아래 규칙에 따라 판단한다. 규칙에 없는 것을 만들지 않는다.

## 카테고리 (반드시 이 중 하나)
- 과업범위: 수급인이 실제로 만들거나 수행해야 하는 일
- 산출물: 제출해야 하는 문서나 결과물
- 일정: 기간, 착수일, 검수 시기
- 보안: 보안, 개인정보, 자료 반출 제한
- 품질: 품질 기준, 성능 요건, 검수 조건
- 계약조건: 하도급, 하자보수, 위반 시 조치, 소유권
- 일반사항: 위 어디에도 들지 않는 배경 설명

## actionable
수급인이 수행해서 완료할 수 있는 일이면 true.
지켜야 할 제약이나 계약 조건이면 false.
보안·계약조건은 대체로 false다. 다만 "보안 점검을 수행한다"처럼
수행할 일이 적혀 있으면 true다.

## confidence
- high: 절 제목과 본문이 카테고리를 분명히 가리킨다
- medium: 그럴듯하지만 다른 카테고리로도 읽힌다
- low: 본문이 짧거나 모호해 확신할 수 없다

확신이 없으면 low로 답한다. 높은 확신을 지어내지 않는다.

## 출력
아래 형식의 JSON만 출력한다. 설명을 덧붙이지 않는다.
{"category": "...", "actionable": true, "confidence": "...", "reason": "한 문장"}"""


def _user_prompt(section: SectionInput) -> str:
    body = section.body[:MAX_BODY_CHARS]
    truncated = "\n(이하 생략)" if len(section.body) > MAX_BODY_CHARS else ""
    return f"절 번호: {section.number}\n절 제목: {section.title}\n\n본문:\n{body}{truncated}"


class FixtureClassifier:
    """분류하지 않는다. 그리고 분류하지 않았다고 말한다.

    로컬 LLM이 설정되지 않았을 때 쓰인다. 조용히 그럴듯한 값을 채우면 화면이
    분류를 마쳤다고 주장하게 되고, 그 주장을 뒷받침하는 것이 아무것도 없다.
    """

    @property
    def name(self) -> str:
        return "fixture"

    def classify(self, sections: list[SectionInput]) -> list[Classification]:
        return [
            Classification.unclassified(
                s.number, "로컬 LLM이 설정되지 않아 분류하지 않았습니다."
            )
            for s in sections
        ]


class OllamaClassifier:
    """사내 GPU의 ollama에 묻는다."""

    def __init__(self, *, base_url: str, model: str, timeout: int) -> None:
        self._base_url = base_url
        self._model = model
        self._timeout = timeout

    @property
    def name(self) -> str:
        return self._model

    def classify(self, sections: list[SectionInput]) -> list[Classification]:
        if not sections:
            return []
        # 절마다 따로 묻는다. 한 번에 몰아서 물으면 모델이 절을 건너뛰거나
        # 순서를 바꿔도 알아채기 어렵다. 하나씩 물으면 어느 절의 답인지 확실하다.
        with ThreadPoolExecutor(max_workers=CONCURRENCY) as pool:
            return list(pool.map(self._classify_one, sections))

    def _classify_one(self, section: SectionInput) -> Classification:
        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": _user_prompt(section)},
            ],
            "response_format": {"type": "json_object"},
            # 분류는 창작이 아니다. 같은 문서를 두 번 돌리면 같은 답이 나와야 한다.
            "temperature": 0,
            "stream": False,
        }

        request = urllib.request.Request(
            f"{self._base_url}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={"content-type": "application/json"},
        )

        try:
            with urllib.request.urlopen(request, timeout=self._timeout) as response:
                body = json.loads(response.read())
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:200]
            logger.warning("classify_http_error", extra={"status": exc.code})
            return Classification.unclassified(
                section.number, f"모델 서버가 {exc.code}로 응답했습니다: {detail}"
            )
        except (urllib.error.URLError, TimeoutError) as exc:
            logger.warning("classify_unreachable")
            return Classification.unclassified(
                section.number, f"모델 서버에 연결하지 못했습니다: {exc}"
            )
        except (ValueError, OSError) as exc:
            return Classification.unclassified(
                section.number, f"모델 응답을 읽지 못했습니다: {exc}"
            )

        return _read_answer(section.number, body)


def _read_answer(number: str, body: dict[str, object]) -> Classification:
    """모델의 답을 우리 타입으로 옮긴다. 규칙을 벗어난 값은 받지 않는다."""

    try:
        choices = body["choices"]
        assert isinstance(choices, list)
        content = choices[0]["message"]["content"]
    except (KeyError, IndexError, TypeError, AssertionError):
        return Classification.unclassified(number, "모델 응답의 형식이 예상과 다릅니다.")

    try:
        answer = json.loads(content)
    except (json.JSONDecodeError, TypeError):
        return Classification.unclassified(number, "모델이 JSON이 아닌 답을 냈습니다.")

    if not isinstance(answer, dict):
        return Classification.unclassified(number, "모델이 JSON 객체를 내지 않았습니다.")

    category = _CATEGORIES.get(str(answer.get("category", "")).strip())
    if category is None or category is Category.UNCLASSIFIED:
        return Classification.unclassified(
            number, f"허용되지 않은 카테고리입니다: {answer.get('category')!r}"
        )

    confidence = _CONFIDENCE.get(str(answer.get("confidence", "")).strip().lower())
    if confidence is None:
        return Classification.unclassified(
            number, f"허용되지 않은 신뢰도입니다: {answer.get('confidence')!r}"
        )

    actionable = answer.get("actionable")
    if not isinstance(actionable, bool):
        return Classification.unclassified(
            number, f"actionable이 참·거짓이 아닙니다: {actionable!r}"
        )

    reason = str(answer.get("reason", "")).strip()[:300]
    return Classification(
        number=number,
        category=category,
        actionable=actionable,
        confidence=confidence,
        reason=reason,
    )


def build_classifier() -> tuple[ClauseClassifier, str | None]:
    """설정에 따라 분류기를 고른다. ``(classifier, unavailable_reason)``.

    실제 어댑터를 요청했는데 설정이 모자라면 픽스처를 돌려주되 사유를 함께
    낸다. 조용히 대체하지 않는다.
    """

    from ....common.adapters import llm_choice

    choice = llm_choice()
    if not choice.use_real:
        return FixtureClassifier(), choice.unavailable_reason

    model = llm_model()
    assert model is not None  # llm_choice가 이미 확인했다
    return (
        OllamaClassifier(
            base_url=llm_base_url(), model=model, timeout=llm_timeout_seconds()
        ),
        None,
    )
