"""Response envelopes defined by ``05_API_AND_EVENT_CONTRACTS.md``.

Every response carries a ``meta.trace_id`` so a user reading an error on screen can
quote something the operator can find in the logs. The trace ID is the same value
the ``X-Trace-ID`` response header carries.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from ..bootstrap.trace import get_trace_id


class Meta(BaseModel):
    model_config = ConfigDict(extra="forbid")

    trace_id: str | None = None


class ListMeta(Meta):
    """Cursor pagination is the default. ``total`` is optional because counting can
    be expensive; endpoints opt in per the contract document."""

    next_cursor: str | None = None
    has_more: bool = False
    total: int | None = None


class Envelope[T](BaseModel):
    model_config = ConfigDict(extra="forbid")

    data: T
    meta: Meta = Field(default_factory=Meta)


class ListEnvelope[T](BaseModel):
    model_config = ConfigDict(extra="forbid")

    data: list[T]
    meta: ListMeta = Field(default_factory=ListMeta)


def single[T](data: T) -> Envelope[T]:
    """Wrap one resource, stamping the current request's trace ID."""

    return Envelope[T](data=data, meta=Meta(trace_id=get_trace_id()))


def collection[T](
    data: list[T],
    *,
    next_cursor: str | None = None,
    has_more: bool = False,
    total: int | None = None,
) -> ListEnvelope[T]:
    """Wrap a page of resources, stamping the current request's trace ID."""

    return ListEnvelope[T](
        data=data,
        meta=ListMeta(
            trace_id=get_trace_id(),
            next_cursor=next_cursor,
            has_more=has_more,
            total=total,
        ),
    )
