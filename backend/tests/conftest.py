from collections.abc import AsyncIterator

import httpx
import pytest
from asgi_lifespan import LifespanManager
from fastapi import FastAPI

from app.core.config import Settings
from app.main import create_app

UNREACHABLE_DB_URL = "postgresql+asyncpg://srm:srm@127.0.0.1:9/srm_credit_none"


@pytest.fixture
def app_settings() -> Settings:
    """Unit-test settings: the database is intentionally unreachable."""
    return Settings(environment="test", database_url=UNREACHABLE_DB_URL, log_json=False)


@pytest.fixture
async def app(app_settings: Settings) -> AsyncIterator[FastAPI]:
    application = create_app(app_settings)
    async with LifespanManager(application):
        yield application


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client
