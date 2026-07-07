"""Idempotent demo seed: market rates and sample assignors.

Reference data required for the engine to work (currencies, receivable types)
is created by the migrations; this script only adds operational demo data so a
fresh `docker compose up` is immediately usable.
"""

import asyncio
from datetime import UTC, datetime
from decimal import Decimal

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.core.logging import setup_logging
from app.domain.enums import RateSource
from app.infrastructure.db.models import Assignor, BaseRate, ExchangeRate

logger = structlog.get_logger()

_EFFECTIVE_AT = datetime(2026, 7, 1, 12, 0, tzinfo=UTC)

_BASE_RATES = (
    ("BRL", Decimal("0.0105")),  # ~CDI mensal
    ("USD", Decimal("0.0035")),  # ~SOFR mensal
)

_EXCHANGE_RATES = (
    ("USD", "BRL", Decimal("5.4200000000")),
    ("BRL", "USD", Decimal("0.1845018450")),
)

_ASSIGNORS = (
    ("Aco Forte Metalurgia LTDA", "11222333000181"),
    ("TecSul Distribuidora SA", "44555666000172"),
    ("Grao do Vale Agro LTDA", "77888999000163"),
)


async def _seed(session: AsyncSession) -> None:
    if await session.scalar(select(func.count()).select_from(BaseRate)):
        logger.info("seed_skipped", reason="base_rates already present")
        return

    for currency_code, monthly_rate in _BASE_RATES:
        session.add(
            BaseRate(
                currency_code=currency_code,
                monthly_rate=monthly_rate,
                effective_at=_EFFECTIVE_AT,
            )
        )
    for base, quote, rate in _EXCHANGE_RATES:
        session.add(
            ExchangeRate(
                base_currency_code=base,
                quote_currency_code=quote,
                rate=rate,
                source=RateSource.MANUAL,
                effective_at=_EFFECTIVE_AT,
            )
        )
    for name, document in _ASSIGNORS:
        session.add(Assignor(name=name, document=document))

    await session.commit()
    logger.info(
        "seed_completed",
        base_rates=len(_BASE_RATES),
        exchange_rates=len(_EXCHANGE_RATES),
        assignors=len(_ASSIGNORS),
    )


async def main() -> None:
    settings = get_settings()
    setup_logging(settings)
    engine = create_async_engine(settings.database_url)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with factory() as session:
            await _seed(session)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
