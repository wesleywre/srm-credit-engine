import asyncio
from collections.abc import AsyncIterator

import pytest
from alembic import command
from alembic.config import Config as AlembicConfig
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import Settings

_MUTABLE_TABLES = (
    "settlement_items",
    "settlements",
    "receivables",
    "batches",
    "assignors",
    "exchange_rates",
    "base_rates",
)


class _TestDatabaseSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SRM_TEST_", env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://srm:srm@localhost:5432/srm_credit_test"


def _admin_url(url: str) -> str:
    base, _, _ = url.rpartition("/")
    return f"{base}/postgres"


@pytest.fixture(scope="session")
def database_url() -> str:
    """Recreate the test database from scratch and apply all migrations."""
    url = _TestDatabaseSettings().database_url
    database_name = url.rpartition("/")[2]

    async def _recreate() -> None:
        admin_engine = create_async_engine(_admin_url(url), isolation_level="AUTOCOMMIT")
        async with admin_engine.connect() as connection:
            await connection.execute(
                text(f'DROP DATABASE IF EXISTS "{database_name}" WITH (FORCE)')
            )
            await connection.execute(text(f'CREATE DATABASE "{database_name}"'))
        await admin_engine.dispose()

    asyncio.run(_recreate())

    alembic_config = AlembicConfig("alembic.ini")
    alembic_config.set_main_option("sqlalchemy.url", url)
    command.upgrade(alembic_config, "head")
    return url


@pytest.fixture
def app_settings(database_url: str) -> Settings:
    """Overrides the unit fixture: integration tests run against real postgres."""
    return Settings(environment="test", database_url=database_url, log_json=False)


@pytest.fixture(autouse=True)
async def _truncate_after_test(database_url: str) -> AsyncIterator[None]:
    yield
    engine = create_async_engine(database_url)
    try:
        async with engine.begin() as connection:
            await connection.execute(text(f"TRUNCATE {', '.join(_MUTABLE_TABLES)} CASCADE"))
    finally:
        await engine.dispose()


@pytest.fixture
async def db_session(database_url: str) -> AsyncIterator[AsyncSession]:
    engine = create_async_engine(database_url)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with factory() as session:
            yield session
    finally:
        await engine.dispose()
