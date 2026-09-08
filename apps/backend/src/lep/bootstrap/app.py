"""FastAPI application factory."""

from __future__ import annotations

import logging
import os
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from pydantic import BaseModel, ConfigDict
from sqlalchemy import text

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


class CheckResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    ok: bool
    #: 실패 사유. 통과했으면 비어 있다.
    detail: str = ""


class HealthReadyResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str
    checks: list[CheckResult]


def _writable(name: str, target: Path) -> CheckResult:
    """디렉터리에 실제로 파일을 하나 써 본다.

    존재 여부만 보면 부족하다. 이름 있는 도커 볼륨은 이미지에 같은 경로가 없으면
    root 소유로 만들어지는데, 그러면 폴더는 있고 쓰기만 막힌다. 그 상태는 첫
    업로드나 첫 지식화에서야 드러난다. 여기서 미리 드러나게 한다.
    """

    probe = target / f".readycheck-{uuid.uuid4().hex}"
    try:
        target.mkdir(parents=True, exist_ok=True)
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
    except OSError as exc:
        return CheckResult(name=name, ok=False, detail=f"{target}: {exc}")
    return CheckResult(name=name, ok=True)


def _database_reachable() -> CheckResult:
    from ..common.db import session_scope

    try:
        with session_scope() as session:
            session.execute(text("select 1"))
    except Exception as exc:  # noqa: BLE001 - 사유를 그대로 보고한다
        return CheckResult(name="database", ok=False, detail=str(exc))
    return CheckResult(name="database", ok=True)


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

    @application.get("/health/ready", response_model=HealthReadyResponse, tags=["health"])
    def health_ready() -> HealthReadyResponse:
        """배포가 실제로 쓸 수 있는 상태인지 본다.

        컨테이너가 떴다는 것과 제품이 동작한다는 것은 다르다. 데이터베이스에
        닿는지, 볼트와 업로드 디렉터리에 쓸 수 있는지를 확인한다. 200이어도
        개별 항목이 실패했을 수 있으므로 ``status``와 ``checks``를 함께 읽는다.

        블로킹 호출이라 ``def``로 둔다. FastAPI가 스레드풀에서 돌린다.
        """

        checks = [
            _database_reachable(),
            _writable("vault", Path(os.getenv("LEP_OBSIDIAN_VAULT", ".vault"))),
            _writable("uploads", Path(os.getenv("LEP_UPLOAD_DIR", ".uploads"))),
        ]
        failed = [c.name for c in checks if not c.ok]
        if failed:
            logger.warning("health_ready_failed", extra={"failed": failed})
        return HealthReadyResponse(
            status="ok" if not failed else "degraded", checks=checks
        )

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
