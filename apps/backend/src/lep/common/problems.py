"""RFC 7807 Problem Details errors.

``05_API_AND_EVENT_CONTRACTS.md`` section 11 fixes the shape and the code
vocabulary. Every problem carries the request trace ID so the value a user reads
on screen matches the one in the logs.

Errors are never reported as successes. ``AGENTS.md`` section 19 forbids it.
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict
from starlette.exceptions import HTTPException as StarletteHTTPException

from ..bootstrap.trace import get_trace_id

PROBLEM_BASE = "https://erp.local/problems"
CONTENT_TYPE = "application/problem+json"

#: Codes this track uses. The wider vocabulary lives in the contract document.
CODE_TITLES: dict[str, str] = {
    "BAD_REQUEST": "요청을 처리할 수 없습니다.",
    "AUTHENTICATION_REQUIRED": "로그인이 필요합니다.",
    "FORBIDDEN": "이 작업을 수행할 권한이 없습니다.",
    "NOT_FOUND": "대상을 찾을 수 없습니다.",
    "STATE_CONFLICT": "현재 상태에서는 처리할 수 없습니다.",
    "VALIDATION_FAILED": "입력값을 확인해 주세요.",
    "INTEGRATION_ERROR": "외부 연동에서 오류가 발생했습니다.",
    "INTERNAL_ERROR": "예기치 못한 오류가 발생했습니다.",
}

CODE_STATUS: dict[str, int] = {
    "BAD_REQUEST": 400,
    "AUTHENTICATION_REQUIRED": 401,
    "FORBIDDEN": 403,
    "NOT_FOUND": 404,
    "STATE_CONFLICT": 409,
    "VALIDATION_FAILED": 422,
    "INTEGRATION_ERROR": 502,
    "INTERNAL_ERROR": 500,
}


class Problem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: str
    title: str
    status: int
    code: str
    detail: str | None = None
    instance: str | None = None
    trace_id: str | None = None
    errors: list[dict[str, Any]] | None = None


class ProblemError(Exception):
    """Raise this from application services instead of returning error tuples."""

    def __init__(
        self,
        code: str,
        detail: str | None = None,
        *,
        errors: list[dict[str, Any]] | None = None,
    ) -> None:
        if code not in CODE_STATUS:
            raise ValueError(f"unknown problem code: {code}")
        super().__init__(detail or code)
        self.code = code
        self.detail = detail
        self.errors = errors

    @property
    def status(self) -> int:
        return CODE_STATUS[self.code]


def not_found(detail: str) -> ProblemError:
    return ProblemError("NOT_FOUND", detail)


def state_conflict(detail: str) -> ProblemError:
    return ProblemError("STATE_CONFLICT", detail)


def _slug(code: str) -> str:
    return code.lower().replace("_", "-")


def _response(
    code: str,
    status: int,
    instance: str,
    detail: str | None,
    errors: list[dict[str, Any]] | None = None,
) -> JSONResponse:
    problem = Problem(
        type=f"{PROBLEM_BASE}/{_slug(code)}",
        title=CODE_TITLES[code],
        status=status,
        code=code,
        detail=detail,
        instance=instance,
        trace_id=get_trace_id(),
        errors=errors,
    )
    return JSONResponse(
        status_code=status,
        content=problem.model_dump(exclude_none=True),
        media_type=CONTENT_TYPE,
    )


def register_problem_handlers(app: FastAPI) -> None:
    """Attach the handlers that turn every failure into Problem Details."""

    @app.exception_handler(ProblemError)
    async def handle_problem(request: Request, exc: ProblemError) -> JSONResponse:
        return _response(exc.code, exc.status, request.url.path, exc.detail, exc.errors)

    @app.exception_handler(RequestValidationError)
    async def handle_validation(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        errors = [
            {"field": ".".join(str(part) for part in error["loc"]), "message": error["msg"]}
            for error in exc.errors()
        ]
        return _response(
            "VALIDATION_FAILED", 422, request.url.path, "입력값이 계약과 맞지 않습니다.", errors
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = {
            400: "BAD_REQUEST",
            401: "AUTHENTICATION_REQUIRED",
            403: "FORBIDDEN",
            404: "NOT_FOUND",
            409: "STATE_CONFLICT",
        }.get(exc.status_code, "INTERNAL_ERROR")
        status = exc.status_code if code != "INTERNAL_ERROR" else 500
        detail = exc.detail if isinstance(exc.detail, str) else None
        return _response(code, status, request.url.path, detail)
