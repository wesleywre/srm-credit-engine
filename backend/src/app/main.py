from fastapi import FastAPI

from app import __version__
from app.api import health
from app.api.error_handlers import register_error_handlers
from app.api.v1 import api_router
from app.core.config import get_settings
from app.core.logging import setup_logging


def create_app() -> FastAPI:
    settings = get_settings()
    setup_logging(settings)

    app = FastAPI(
        title="SRM Credit Engine",
        description="Multi-currency receivables pricing and settlement platform.",
        version=__version__,
        openapi_url=f"{settings.api_v1_prefix}/openapi.json",
    )
    register_error_handlers(app)
    app.include_router(health.router)
    app.include_router(api_router, prefix=settings.api_v1_prefix)
    return app


app = create_app()
