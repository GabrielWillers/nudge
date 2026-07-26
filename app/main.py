"""Composição do serviço: um processo, uma imagem (ADR-0010).

Pontos de contato com a plataforma, e só eles: `/healthz`, `/readyz`,
`/metrics` e o identificador de build exposto na página.
"""

import logging
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from pathlib import Path

from alembic import command
from alembic.config import Config
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from prometheus_fastapi_instrumentator import Instrumentator

from app.config import get_settings
from app.db import database_ready
from app.routes import router

APP_DIR = Path(__file__).parent
MAX_BODY_BYTES = 16 * 1024

logger = logging.getLogger("nudge")


def run_migrations() -> None:
    """Aplica as migrações pendentes antes de o processo atender.

    Correto com uma réplica e quebra com mais de uma (ADR-0007): escalar exige
    extrair este passo do ciclo de vida do serviço.
    """
    config = Config()
    config.set_main_option("script_location", str(APP_DIR / "migrations"))
    command.upgrade(config, "head")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    logging.basicConfig(level=settings.log_level.upper())
    logger.info(
        "iniciando nudge version=%s commit=%s",
        settings.app_version,
        settings.app_commit,
    )
    run_migrations()
    yield


def create_app() -> FastAPI:
    # Falha imediatamente, com mensagem explícita, se DATABASE_URL não existir.
    settings = get_settings()

    app = FastAPI(
        title="Nudge",
        version=settings.app_version,
        lifespan=lifespan,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )

    @app.middleware("http")
    async def limit_body_size(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        declared = request.headers.get("content-length")
        if (
            declared is not None
            and declared.isdigit()
            and int(declared) > MAX_BODY_BYTES
        ):
            return PlainTextResponse(
                "corpo de requisição muito grande", status_code=413
            )
        return await call_next(request)

    @app.get("/healthz", include_in_schema=False)
    def healthz() -> JSONResponse:
        """Sonda de vivacidade. **Nunca** toca o banco (invariante do PRD):
        se tocasse, uma indisponibilidade do banco causaria reinício em laço."""
        return JSONResponse(
            {
                "status": "ok",
                "version": settings.app_version,
                "commit": settings.app_commit,
            }
        )

    @app.get("/readyz", include_in_schema=False)
    def readyz() -> JSONResponse:
        """Sonda de prontidão: depende do banco, para que uma instância sem
        banco deixe de receber tráfego."""
        if database_ready():
            return JSONResponse({"status": "ready", "database": "up"})
        return JSONResponse(
            {"status": "unavailable", "database": "down"}, status_code=503
        )

    @app.get("/version", include_in_schema=False)
    def version() -> JSONResponse:
        return JSONResponse(
            {"version": settings.app_version, "commit": settings.app_commit}
        )

    app.mount("/static", StaticFiles(directory=str(APP_DIR / "static")), name="static")
    app.include_router(router)

    Instrumentator(excluded_handlers=["/metrics", "/healthz", "/readyz"]).instrument(
        app
    ).expose(app, endpoint="/metrics", include_in_schema=False)

    return app


app = create_app()
