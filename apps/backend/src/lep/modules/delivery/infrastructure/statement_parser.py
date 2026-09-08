"""Turn an uploaded statement of work into clauses.

kordoc parses hwpx, hwp, docx and pdf into Markdown. That is its primary purpose,
and it is already in the image, so the upload path reuses it rather than adding
another document library.

Splitting the Markdown into 조항 is a regular expression over the Korean article
headings (제3조, 제3조 2항, and the 1. / 가. outline forms). **This is not
classification.** Deciding which clause is an actionable task, in what category,
with what confidence, is the local LLM's job and arrives in WP-PKD-033. Until
then every clause is emitted as 미분류 at low confidence, which is what the
screen shows and what the promote-to-task guard refuses to act on. Reporting
anything higher would put a number on screen that nothing earned.
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

from ....common.adapters import kordoc_cli, kordoc_use_npx

TIMEOUT_SECONDS = 180

#: kordoc이 한글을 UTF-8로 낸다. 로케일 인코딩으로 읽으면 한국어 윈도우에서
#: 읽기 스레드가 터진다. 리눅스 컨테이너에서도 명시하는 편이 안전하다.
OUTPUT_ENCODING = "utf-8"

SUPPORTED_SUFFIXES = {".hwpx", ".hwp", ".docx", ".pdf", ".md", ".txt"}

#: 제3조, 제3조 2항, 제 3 조 형태를 모두 잡는다.
ARTICLE = re.compile(r"^\s*(?:#{1,6}\s*)?(제\s*\d+\s*조(?:\s*제?\s*\d+\s*항)?)\s*[.．)\]]?\s*(.*)$")
#: 1. / 1) / 가. 형태의 개조식 항목.
OUTLINE = re.compile(r"^\s*(?:#{1,6}\s*)?((?:\d{1,2}|[가-힣])[.)])\s+(.+)$")

#: 조항 본문이 이보다 짧으면 제목만 있고 내용이 없는 줄로 본다.
MIN_BODY_LENGTH = 4


@dataclass(frozen=True, slots=True)
class ParsedClause:
    ordinal: int
    article: str
    text: str


@dataclass(frozen=True, slots=True)
class ParseResult:
    """파싱 결과. 실패를 성공으로 숨기지 않는다."""

    markdown: str
    clauses: list[ParsedClause]
    error: str | None = None

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


def to_markdown(path: Path) -> tuple[str, str | None]:
    """문서를 마크다운으로 바꾼다. ``(markdown, error)``."""

    suffix = path.suffix.lower()
    if suffix in {".md", ".txt"}:
        try:
            return path.read_text(encoding="utf-8", errors="replace"), None
        except OSError as exc:
            return "", f"파일을 읽지 못했습니다: {exc}"

    if suffix not in SUPPORTED_SUFFIXES:
        return "", f"지원하지 않는 형식입니다: {suffix or '확장자 없음'}"

    try:
        result = subprocess.run(  # noqa: S603
            [*_command(), str(path)],
            capture_output=True,
            timeout=TIMEOUT_SECONDS,
            check=False,
            text=True,
            encoding=OUTPUT_ENCODING,
            errors="replace",
        )
    except FileNotFoundError:
        return "", "문서 변환기를 실행할 수 없습니다. kordoc 설정을 확인해 주세요."
    except subprocess.TimeoutExpired:
        return "", f"문서 분석이 {TIMEOUT_SECONDS}초 안에 끝나지 않았습니다."
    except OSError as exc:
        return "", f"문서 변환기를 실행하지 못했습니다: {exc}"

    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip().splitlines()
        return "", detail[-1] if detail else "문서 변환기가 오류로 종료했습니다."

    text = result.stdout.strip()
    if not text:
        return "", "문서에서 읽어낼 내용이 없습니다."
    return text, None


def split_clauses(markdown: str) -> list[ParsedClause]:
    """마크다운을 조항 단위로 쪼갠다.

    제N조가 하나도 없으면 개조식 항목으로 떨어진다. 그것도 없으면 빈 목록을
    돌려주고, 화면은 "조항을 찾지 못했다"고 말한다. 억지로 문단을 쪼개
    조항인 척하지 않는다.
    """

    lines = markdown.splitlines()
    found: list[tuple[str, list[str]]] = []

    for pattern in (ARTICLE, OUTLINE):
        found = []
        current: tuple[str, list[str]] | None = None
        for line in lines:
            match = pattern.match(line)
            if match:
                if current is not None:
                    found.append(current)
                label = re.sub(r"\s+", " ", match.group(1)).strip()
                current = (label, [match.group(2).strip()] if match.group(2).strip() else [])
            elif current is not None and line.strip():
                current[1].append(line.strip())
        if current is not None:
            found.append(current)
        if found:
            break

    clauses: list[ParsedClause] = []
    for index, (label, body) in enumerate(found, start=1):
        text = " ".join(body).strip()
        if len(text) < MIN_BODY_LENGTH:
            continue
        # 화면의 한 줄에 들어갈 만큼만 남긴다. 원문은 마크다운에 그대로 있다.
        clauses.append(
            ParsedClause(ordinal=index, article=label, text=text[:300])
        )
    return clauses


def parse(path: Path) -> ParseResult:
    markdown, error = to_markdown(path)
    if error is not None:
        return ParseResult(markdown="", clauses=[], error=error)
    return ParseResult(markdown=markdown, clauses=split_clauses(markdown))
