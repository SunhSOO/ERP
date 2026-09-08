"""Turn an uploaded statement of work into a section tree.

kordoc parses hwpx, hwp, docx and pdf into Markdown. It is already in the image,
so the upload path reuses it rather than adding another document library.

**Scanned PDFs.** A PDF from a client is often a scan with no text layer. kordoc
then succeeds and returns almost nothing — one image reference for thirty pages.
That reads as "no clauses found" when the truth is "nobody read the document".
So a conversion that comes back effectively empty is retried with OCR, which is
slow enough that it must not be the default and useful enough that it must not
be skipped.

**Structure.** Korean public-sector statements of work do not use 제N조. They use
a decimal outline — ``1.과업의 개요`` then ``1.1과업명`` — with ``O``, ``ㅇ`` and
``-`` as bullet markers inside a section. Splitting on that outline is a rule,
not a judgement: the numbering is exact, so the same document always yields the
same sections and the reason for every split can be pointed at.

**This is still not classification.** Which section is an actionable task, in
what category, with what confidence, is the local LLM's job (WP-PKD-033). Until
then every clause is emitted as 미분류 at low confidence, which is what the
screen shows and what the promote-to-task guard refuses to act on.
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from ....common.adapters import kordoc_cli, kordoc_use_npx

TIMEOUT_SECONDS = 180

#: OCR은 페이지마다 모델을 돌린다. 31쪽 스캔본이 1분 안팎이라 여유를 크게 준다.
OCR_TIMEOUT_SECONDS = 900

#: kordoc이 한글을 UTF-8로 낸다. 로케일 인코딩으로 읽으면 한국어 윈도우에서
#: 읽기 스레드가 터진다. 리눅스 컨테이너에서도 명시하는 편이 안전하다.
OUTPUT_ENCODING = "utf-8"

SUPPORTED_SUFFIXES = {".hwpx", ".hwp", ".docx", ".pdf", ".md", ".txt"}

#: 이미지 참조만 남은 변환 결과. 스캔본을 텍스트로 읽었을 때 나온다.
IMAGE_ONLY = re.compile(r"!\[[^\]]*\]\([^)]*\)")

#: 이보다 적은 글자가 남으면 문서를 읽지 못한 것으로 본다. 표지만 있는 문서와
#: 스캔본을 가르는 선이다. 실제 스캔본은 23바이트, 이 문서는 44,000자였다.
MEANINGFUL_TEXT_MIN = 200

#: 제3조, 제3조 2항, 제 3 조 형태를 모두 잡는다.
ARTICLE = re.compile(r"^\s*(?:#{1,6}\s*)?(제\s*\d+\s*조(?:\s*제?\s*\d+\s*항)?)\s*[.．)\]]?\s*(.*)$")

#: 1. / 1.1 / 2.1.3 형태의 십진 개조식. 점 뒤 공백은 있어도 없어도 된다.
#: 공공 과업지시서의 표준 형태이고 `1.1과업명`처럼 붙여 쓰는 경우가 흔하다.
DECIMAL = re.compile(
    # 번호 뒤에 닫는 괄호가 오면 `1) 대상 시설`처럼 절 안의 항목이다. 제목이 아니다.
    r"^\s*(?:#{1,6}\s*)?(\d{1,2}(?:\.\d{1,2})*)\.?\s*(?![)\]])(\S.*)$"
)

#: 가. / 1) 형태. 십진 번호가 없는 문서의 마지막 기댓값이다.
OUTLINE = re.compile(r"^\s*(?:#{1,6}\s*)?((?:\d{1,2}|[가-힣])[.)])\s+(.+)$")

#: 절 안의 항목 표시. 제목이 아니라 본문이다.
BULLETS = ("O", "o", "ㅇ", "○", "●", "-", "·", "※", "□", "▪")

#: 제목에 최소한 이만큼의 글자가 있어야 한다. OCR 잡음을 거른다.
MIN_TITLE_LENGTH = 2

#: 조항 본문이 이보다 짧으면 제목만 있고 내용이 없는 줄로 본다.
MIN_BODY_LENGTH = 4

_HANGUL_OR_LATIN = re.compile(r"[가-힣A-Za-z]")


@dataclass(frozen=True, slots=True)
class ParsedClause:
    ordinal: int
    article: str
    text: str
    #: 십진 번호의 깊이. `1`은 1, `1.1`은 2. 제N조 형식이면 1.
    level: int = 1
    #: 상위 절의 번호. 최상위면 ``None``. 볼트 노트의 링크가 이걸 쓴다.
    parent: str | None = None
    #: 절의 본문 전체. 화면에 쓰는 `text`는 이걸 줄인 것이다.
    body: str = ""


@dataclass(frozen=True, slots=True)
class ParseResult:
    """파싱 결과. 실패를 성공으로 숨기지 않는다."""

    markdown: str
    clauses: list[ParsedClause] = field(default_factory=list)
    error: str | None = None
    #: OCR로 다시 읽었으면 참. 화면이 왜 오래 걸렸는지 설명할 수 있다.
    used_ocr: bool = False

    @property
    def succeeded(self) -> bool:
        return self.error is None


def _command() -> list[str]:
    cli = kordoc_cli()
    if cli:
        return ["node", cli]
    if kordoc_use_npx():
        return ["npx", "--yes", "kordoc"]
    return ["kordoc"]


def meaningful_length(markdown: str) -> int:
    """이미지 참조와 공백을 뺀 실제 글자 수."""

    return len(re.sub(r"\s+", "", IMAGE_ONLY.sub("", markdown)))


def _run(path: Path, *, ocr: bool) -> tuple[str, str | None]:
    argv = [*_command()]
    if ocr:
        argv.append("--ocr")
    argv.append(str(path))

    try:
        result = subprocess.run(  # noqa: S603
            argv,
            capture_output=True,
            timeout=OCR_TIMEOUT_SECONDS if ocr else TIMEOUT_SECONDS,
            check=False,
            text=True,
            encoding=OUTPUT_ENCODING,
            errors="replace",
        )
    except FileNotFoundError:
        return "", "문서 변환기를 실행할 수 없습니다. kordoc 설정을 확인해 주세요."
    except subprocess.TimeoutExpired:
        limit = OCR_TIMEOUT_SECONDS if ocr else TIMEOUT_SECONDS
        return "", f"문서 분석이 {limit}초 안에 끝나지 않았습니다."
    except OSError as exc:
        return "", f"문서 변환기를 실행하지 못했습니다: {exc}"

    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip().splitlines()
        return "", detail[-1] if detail else "문서 변환기가 오류로 종료했습니다."

    return result.stdout.strip(), None


def to_markdown(path: Path) -> tuple[str, str | None, bool]:
    """문서를 마크다운으로 바꾼다. ``(markdown, error, used_ocr)``.

    변환은 됐는데 읽어낸 글자가 거의 없으면 스캔본으로 보고 OCR로 한 번 더
    시도한다. 텍스트 레이어가 있는 문서는 첫 번째에서 끝나므로 느려지지 않고,
    스캔본만 대가를 치른다.
    """

    suffix = path.suffix.lower()
    if suffix in {".md", ".txt"}:
        try:
            return path.read_text(encoding="utf-8", errors="replace"), None, False
        except OSError as exc:
            return "", f"파일을 읽지 못했습니다: {exc}", False

    if suffix not in SUPPORTED_SUFFIXES:
        return "", f"지원하지 않는 형식입니다: {suffix or '확장자 없음'}", False

    text, error = _run(path, ocr=False)
    if error is not None:
        return "", error, False

    if meaningful_length(text) >= MEANINGFUL_TEXT_MIN:
        return text, None, False

    # 여기까지 왔으면 변환은 성공했는데 읽을 글자가 없다. 스캔본이다.
    ocr_text, ocr_error = _run(path, ocr=True)
    if ocr_error is not None:
        # OCR까지 실패했으면 두 사실을 다 말한다. 어느 쪽이 문제인지 알아야 한다.
        return "", f"문서에 텍스트가 없어 OCR로 다시 시도했지만 실패했습니다: {ocr_error}", True

    if meaningful_length(ocr_text) < MEANINGFUL_TEXT_MIN:
        return "", "문서에서 읽어낼 내용이 없습니다. 스캔 품질을 확인해 주세요.", True

    return ocr_text, None, True


def _is_heading_title(title: str) -> bool:
    """제목처럼 보이는지. OCR 잡음과 표 안의 숫자를 거른다."""

    stripped = title.strip()
    if len(stripped) < MIN_TITLE_LENGTH:
        return False
    return bool(_HANGUL_OR_LATIN.search(stripped))


def _parent_of(number: str) -> str | None:
    head, _, _ = number.rpartition(".")
    return head or None


def _drop_table_of_contents(
    sections: list[tuple[str, str, list[str]]],
) -> list[tuple[str, str, list[str]]]:
    """목차 항목을 걷어낸다.

    목차는 같은 번호가 본문에서 다시 나오고, 목차 쪽에는 본문이 붙지 않는다.
    그 두 조건이 함께 참인 것만 버린다. 본문이 짧은 진짜 절을 지우지 않도록
    번호가 뒤에 다시 나오는지를 반드시 함께 본다.
    """

    later: dict[str, int] = {}
    for index, (number, _, _) in enumerate(sections):
        later[number] = index

    kept: list[tuple[str, str, list[str]]] = []
    for index, section in enumerate(sections):
        number, _, body = section
        body_text = " ".join(body).strip()
        if len(body_text) < MIN_BODY_LENGTH and later[number] > index:
            continue
        kept.append(section)
    return kept


def _collect(lines: list[str], pattern: re.Pattern[str], *, decimal: bool) -> list[
    tuple[str, str, list[str]]
]:
    """``(번호, 제목, 본문 줄들)``의 목록으로 모은다."""

    found: list[tuple[str, str, list[str]]] = []
    current: tuple[str, str, list[str]] | None = None

    for line in lines:
        stripped = line.strip()
        # 항목 표시로 시작하는 줄은 본문이다. 제목으로 오인하지 않는다.
        bullet = stripped.startswith(BULLETS)
        match = None if bullet else pattern.match(line)

        if match and (not decimal or _is_heading_title(match.group(2))):
            if current is not None:
                found.append(current)
            label = re.sub(r"\s+", " ", match.group(1)).strip()
            title = match.group(2).strip() if decimal else ""
            rest = "" if decimal else match.group(2).strip()
            current = (label, title, [rest] if rest else [])
        elif current is not None and stripped:
            current[2].append(stripped)

    if current is not None:
        found.append(current)
    return found


def split_clauses(markdown: str) -> list[ParsedClause]:
    """마크다운을 절 단위로 쪼갠다.

    세 가지 표기를 순서대로 시도한다. 제N조, 십진 번호, 그리고 가./1) 개조식.
    셋 다 없으면 빈 목록을 돌려주고 화면이 "조항을 찾지 못했다"고 말한다.
    억지로 문단을 쪼개 조항인 척하지 않는다.
    """

    lines = markdown.splitlines()

    for pattern, decimal in ((ARTICLE, False), (DECIMAL, True), (OUTLINE, False)):
        found = _collect(lines, pattern, decimal=decimal)
        if decimal:
            found = _drop_table_of_contents(found)
        if not found:
            continue

        clauses: list[ParsedClause] = []
        for index, (number, title, body) in enumerate(found, start=1):
            body_text = " ".join(body).strip()
            # 제N조는 제목 자리가 없어 본문 첫머리가 곧 제목이다.
            headline = title or body_text
            # 길이 기준은 본문에서 제목을 끌어다 쓸 때만 건다. 십진 절의 제목은
            # `과업명`이나 `하도급`처럼 세 글자짜리가 흔하고, 그건 잡음이 아니라
            # 진짜 절 이름이다. 여기에 같은 기준을 걸면 그 절들이 통째로 사라진다.
            if not title and len(headline) < MIN_BODY_LENGTH:
                continue
            if title and not _is_heading_title(title):
                continue
            clauses.append(
                ParsedClause(
                    ordinal=index,
                    article=number,
                    # 화면 한 줄에 들어갈 만큼만. 원문은 body에 그대로 있다.
                    text=headline[:300],
                    level=number.count(".") + 1 if decimal else 1,
                    parent=_parent_of(number) if decimal else None,
                    body=body_text,
                )
            )
        if clauses:
            return clauses

    return []


def parse(path: Path) -> ParseResult:
    markdown, error, used_ocr = to_markdown(path)
    if error is not None:
        return ParseResult(markdown="", clauses=[], error=error, used_ocr=used_ocr)
    return ParseResult(
        markdown=markdown, clauses=split_clauses(markdown), used_ocr=used_ocr
    )
