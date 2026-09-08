"""Splitting a statement of work into sections.

The shapes here are taken from a real client document: a scanned 31-page PDF
from a water treatment AI project, read back with OCR. Every case that used to
produce zero clauses on that file has a test.
"""

from __future__ import annotations

from lep.modules.delivery.infrastructure.statement_parser import (
    meaningful_length,
    split_clauses,
)

# 공공 과업지시서의 실제 형태. 목차가 앞에 오고, 절 제목에 점 뒤 공백이 없으며,
# 항목은 O와 ㅇ와 -로 시작한다.
GOVERNMENT_FORM = """정수장 데이터 전처리 및 AI 개발 용역

과업지시서

2026. 04.

목차

1.과업의 개요
2.과업의 수행방법 및 세부내용
3.과업수행 일반사항

1.과업의 개요

1.1과업명

O정수장 데이터 전처리 및 AI 개발 용역

1.2 과업 목적

ㅇ운영상태를 실시간으로 분석, 진단, 예측한다
-최적 운전인자를 도출한다

1.3 과업 기간

O착수일로부터 255일
※불가피한 상황 발생시 상호협의하여 조정할 수 있음

2.과업의 수행방법 및 세부내용

2.1.과업수행방법

1) 대상 시설
2) 수행 절차

3.과업수행 일반사항

3.6 하도급

O수급인은 하도급 시 발주자의 승인을 받아야 한다
"""


def test_decimal_outline_is_split_into_a_section_tree() -> None:
    """이 문서에는 제N조가 하나도 없다. 공공 과업지시서의 표준 형태다."""

    clauses = split_clauses(GOVERNMENT_FORM)
    numbers = [c.article for c in clauses]

    assert numbers == ["1", "1.1", "1.2", "1.3", "2", "2.1", "3", "3.6"]


def test_section_depth_and_parent_come_from_the_number() -> None:
    by_number = {c.article: c for c in split_clauses(GOVERNMENT_FORM)}

    assert by_number["1"].level == 1
    assert by_number["1"].parent is None
    assert by_number["1.1"].level == 2
    assert by_number["1.1"].parent == "1"
    assert by_number["2.1"].parent == "2"


def test_a_heading_without_a_space_after_the_dot_still_counts() -> None:
    """`1.1과업명`은 붙여 쓴다. 공백을 요구하면 이 문서 전체가 0개가 된다."""

    by_number = {c.article: c for c in split_clauses(GOVERNMENT_FORM)}

    assert by_number["1.1"].text == "과업명"


def test_a_three_letter_section_title_is_kept() -> None:
    """`과업명`과 `하도급`은 세 글자다. 길이로 거르면 진짜 절이 사라진다."""

    numbers = [c.article for c in split_clauses(GOVERNMENT_FORM)]

    assert "1.1" in numbers
    assert "3.6" in numbers


def test_a_numbered_list_item_is_body_not_a_heading() -> None:
    """`1) 대상 시설`은 절 안의 항목이다. 이것을 1번 절로 읽으면 번호가 꼬인다."""

    by_number = {c.article: c for c in split_clauses(GOVERNMENT_FORM)}

    assert "대상 시설" in by_number["2.1"].body
    # 2.1 뒤에 1번 절이 새로 생기지 않았다.
    assert [c.article for c in split_clauses(GOVERNMENT_FORM)].count("1") == 1


def test_the_table_of_contents_is_not_mistaken_for_sections() -> None:
    """목차는 같은 번호를 본문보다 먼저 내놓고 내용이 없다."""

    clauses = split_clauses(GOVERNMENT_FORM)

    # 1번이 두 번(목차 + 본문) 잡히지 않았다.
    assert [c.article for c in clauses].count("1") == 1
    # 본문 쪽 1번이 남았으므로 그 아래 절들이 붙어 있다.
    assert [c.article for c in clauses if c.parent == "1"] == ["1.1", "1.2", "1.3"]


def test_bullet_markers_stay_in_the_body() -> None:
    by_number = {c.article: c for c in split_clauses(GOVERNMENT_FORM)}

    assert "255일" in by_number["1.3"].body
    assert "상호협의" in by_number["1.3"].body


def test_a_year_line_is_not_a_section() -> None:
    """`2026. 04.`는 표지의 날짜다. 숫자로 시작한다고 절이 되지 않는다."""

    assert "2026" not in {c.article for c in split_clauses(GOVERNMENT_FORM)}
    assert "20" not in {c.article for c in split_clauses(GOVERNMENT_FORM)}


ARTICLE_FORM = """제1조 (목적)
이 계약은 시스템 구축을 목적으로 한다.

제2조 (과업 범위)
수급인은 다음 각 호의 업무를 수행한다.
"""


def test_the_article_form_still_works() -> None:
    """계약서 형태의 문서는 여전히 제N조로 나뉜다."""

    clauses = split_clauses(ARTICLE_FORM)

    assert [c.article for c in clauses] == ["제1조", "제2조"]
    assert clauses[0].level == 1
    assert clauses[0].parent is None


def test_a_document_with_no_structure_yields_nothing() -> None:
    """억지로 문단을 쪼개 조항인 척하지 않는다."""

    assert split_clauses("본문만 있는 문서입니다.\n계속 이어집니다.") == []


def test_meaningful_length_ignores_image_references() -> None:
    """스캔본을 텍스트로 읽으면 31쪽이 이미지 참조 한 줄로 나온다.

    이 값이 OCR로 다시 읽을지를 정하므로, 이미지 참조를 내용으로 세면
    스캔본이 정상 변환으로 통과해 버린다.
    """

    assert meaningful_length("![image](image_001.png)") == 0
    assert meaningful_length("과업지시서\n\n![image](x.png)\n") == 5
