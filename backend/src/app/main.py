from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app import __version__
from app.api import health
from app.api.error_handlers import register_error_handlers
from app.api.v1 import api_router
from app.core.config import Settings, get_settings
from app.core.logging import setup_logging
from app.infrastructure.db.engine import create_engine, create_session_factory


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings: Settings = app.state.settings
    engine = create_engine(settings)
    app.state.engine = engine
    app.state.session_factory = create_session_factory(engine)
    yield
    await engine.dispose()


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    setup_logging(settings)

    app = FastAPI(
        title="SRM Credit Engine",
        description="Multi-currency receivables pricing and settlement platform.",
        version=__version__,
        openapi_url=f"{settings.api_v1_prefix}/openapi.json",
        lifespan=_lifespan,
    )
    app.state.settings = settings
    register_error_handlers(app)
    app.include_router(health.router)
    app.include_router(api_router, prefix=settings.api_v1_prefix)
    return app


app = create_app()
