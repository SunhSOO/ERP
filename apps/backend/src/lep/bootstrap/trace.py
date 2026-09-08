"""Request trace ID context and middleware."""

from __future__ import annotations

import re
from contextvars import ContextVar, Token
from uuid import uuid4

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

_TRACE_ID: ContextVar[str | None] = ContextVar("lep_trace_id", default=None)
_SAFE_REQUEST_ID = re.compile(r"^[A-Za-z0-9._:-]{1,64}$")


def resolve_trace_id(request_id: str | None) -> str:
    if request_id is not None and _SAFE_REQUEST_ID.fullmatch(request_id):
        return request_id
    return str(uuid4())


def set_trace_id(value: str) -> Token[str | None]:
    return _TRACE_ID.set(value)


def reset_trace_id(token: Token[str | None]) -> None:
    _TRACE_ID.reset(token)


def get_trace_id() -> str | None:
    return _TRACE_ID.get()


class TraceIdMiddleware(BaseHTTPMiddleware):
    """Attach a safe trace ID to every response and request log context."""

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        trace_id = resolve_trace_id(request.headers.get("X-Request-ID"))
        token = set_trace_id(trace_id)
        try:
            response = await call_next(request)
            response.headers["X-Trace-ID"] = trace_id
            return response
        finally:
            reset_trace_id(token)
