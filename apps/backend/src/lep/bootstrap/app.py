"""FastAPI application factory."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from pydantic import BaseModel, ConfigDict

from ..common.problems import register_problem_handlers
from ..common.schema import create_all
from ..modules.delivery.api.routes import router as delivery_router
from ..modules.documents.api.routes import router as documents_router
from ..modules.iam.api.routes import router as auth_router
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


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """빈 데이터베이스에 스키마를 만든다.

    기동을 막지 않는다. 데이터베이스가 아직 뜨지 않았으면 죽는 대신 사유를
    남긴다. compose의 헬스체크가 통과해야 의존 서비스가 시작되므로, 여기서
    죽으면 교착이 된다.
    """

    try:
        create_all()
    except Exception:  # noqa: BLE001 - 기동을 막지 않되 숨기지도 않는다
        logging.getLogger("lep.bootstrap").exception("schema_setup_failed")
    yield


def create_app(settings: Settings | None = None) -> FastAPI:
    runtime = settings or Settings.from_env()
    configure_logging(runtime.log_level)
    application = FastAPI(
        title="Luminode Platform API", version="0.2.0", lifespan=lifespan
    )
    application.add_middleware(TraceIdMiddleware)
    register_problem_handlers(application)
    logger = logging.getLogger("lep.request")

    @application.get("/health/live", response_model=HealthLiveResponse, tags=["health"])
    async def health_live() -> HealthLiveResponse:
        """Process liveness only. It does not touch the database on purpose:
        the container must be able to report itself alive while the database is
        still starting, or compose deadlocks on its own healthcheck."""

        logger.info("health_live")
        return HealthLiveResponse(status="ok", service=runtime.service_name)

    # 각 모듈이 자기 라우트를 소유한다. bootstrap은 붙이기만 한다.
    application.include_router(auth_router)
    application.include_router(projects_router)
    application.include_router(delivery_router)
    application.include_router(knowledge_router)
    application.include_router(documents_router)
    application.include_router(mail_router)
    application.include_router(integrations_router)

    return application


app = create_app()
