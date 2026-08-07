"""FastAPI application factory for the repository foundation."""

from __future__ import annotations

import logging

from fastapi import FastAPI
from pydantic import BaseModel, ConfigDict

from .config import Settings
from .logging_setup import configure_logging
from .trace import TraceIdMiddleware


class HealthLiveResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str
    service: str


def create_app(settings: Settings | None = None) -> FastAPI:
    runtime = settings or Settings.from_env()
    configure_logging(runtime.log_level)
    application = FastAPI(title="Luminode ERP Platform API", version="0.1.0")
    application.add_middleware(TraceIdMiddleware)
    logger = logging.getLogger("lep.request")

    @application.get("/health/live", response_model=HealthLiveResponse, tags=["health"])
    async def health_live() -> HealthLiveResponse:
        logger.info("health_live")
        return HealthLiveResponse(status="ok", service=runtime.service_name)

    return application


app = create_app()
