"""FastAPI application factory."""

from __future__ import annotations

import logging

from fastapi import FastAPI
from pydantic import BaseModel, ConfigDict

from ..common.problems import register_problem_handlers
from ..modules.delivery.api.routes import router as delivery_router
from ..modules.documents.api.routes import router as documents_router
from ..modules.integrations.api.routes import router as integrations_router
from ..modules.knowledge.api.routes import router as knowledge_router
from ..modules.mail.api.routes import router as mail_router
from ..modules.projects.api.routes import router as projects_router
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
    register_problem_handlers(application)
    logger = logging.getLogger("lep.request")

    @application.get("/health/live", response_model=HealthLiveResponse, tags=["health"])
    async def health_live() -> HealthLiveResponse:
        logger.info("health_live")
        return HealthLiveResponse(status="ok", service=runtime.service_name)

    # Each module owns its routes. The bootstrap package only mounts them; it never
    # reaches past a module's public surface.
    application.include_router(projects_router)
    application.include_router(delivery_router)
    application.include_router(knowledge_router)
    application.include_router(documents_router)
    application.include_router(mail_router)
    application.include_router(integrations_router)

    return application


app = create_app()
