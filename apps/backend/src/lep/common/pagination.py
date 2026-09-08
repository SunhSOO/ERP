"""Cursor pagination helpers.

The contract document makes cursor pagination the default. At fixture scale the
cursor is just an offset, but keeping the shape now means the SQL adapters added
in WP-PKD-020 can swap in a keyset cursor without changing any route or client.
"""

from __future__ import annotations

import base64
import binascii
from dataclasses import dataclass

from .problems import ProblemError

DEFAULT_LIMIT = 50
MAX_LIMIT = 200


def encode_cursor(offset: int) -> str:
    return base64.urlsafe_b64encode(f"o:{offset}".encode()).decode().rstrip("=")


def decode_cursor(cursor: str | None) -> int:
    if cursor is None:
        return 0
    padded = cursor + "=" * (-len(cursor) % 4)
    try:
        raw = base64.urlsafe_b64decode(padded.encode()).decode()
    except (binascii.Error, UnicodeDecodeError) as exc:
        raise ProblemError("BAD_REQUEST", f"cursor를 해석할 수 없습니다: {exc}") from exc
    if not raw.startswith("o:"):
        raise ProblemError("BAD_REQUEST", "cursor 형식이 올바르지 않습니다.")
    try:
        offset = int(raw[2:])
    except ValueError as exc:
        raise ProblemError("BAD_REQUEST", "cursor 형식이 올바르지 않습니다.") from exc
    if offset < 0:
        raise ProblemError("BAD_REQUEST", "cursor 형식이 올바르지 않습니다.")
    return offset


@dataclass(frozen=True, slots=True)
class PageResult[TItem]:
    items: list[TItem]
    next_cursor: str | None
    has_more: bool
    total: int


def paginate[TItem](
    items: list[TItem], *, cursor: str | None = None, limit: int = DEFAULT_LIMIT
) -> PageResult[TItem]:
    """Slice an in-memory collection into one page."""

    if limit < 1 or limit > MAX_LIMIT:
        raise ProblemError("BAD_REQUEST", f"limit은 1 이상 {MAX_LIMIT} 이하여야 합니다.")

    offset = decode_cursor(cursor)
    window = items[offset : offset + limit]
    consumed = offset + len(window)
    has_more = consumed < len(items)

    return PageResult(
        items=window,
        next_cursor=encode_cursor(consumed) if has_more else None,
        has_more=has_more,
        total=len(items),
    )
