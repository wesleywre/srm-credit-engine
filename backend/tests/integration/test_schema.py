from datetime import UTC, datetime
from decimal import Decimal

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.models import Assignor, Currency, ExchangeRate, ReceivableType

pytestmark = pytest.mark.integration


async def test_reference_data_is_seeded_by_migration(db_session: AsyncSession) -> None:
    currencies = (await db_session.scalars(select(Currency).order_by(Currency.code))).all()
    types = (await db_session.scalars(select(ReceivableType).order_by(ReceivableType.id))).all()

    assert [currency.code for currency in currencies] == ["BRL", "USD"]
    assert [(t.code, t.monthly_spread) for t in types] == [
        ("DUPLICATA", Decimal("0.015000")),
        ("CHEQUE", Decimal("0.025000")),
    ]


async def test_exchange_rate_tick_is_unique_per_pair(db_session: AsyncSession) -> None:
    effective_at = datetime(2026, 7, 1, 12, 0, tzinfo=UTC)
    first = ExchangeRate(
        base_currency_code="USD",
        quote_currency_code="BRL",
        rate=Decimal("5.42"),
        source="MANUAL",
        effective_at=effective_at,
    )
    duplicate = ExchangeRate(
        base_currency_code="USD",
        quote_currency_code="BRL",
        rate=Decimal("5.43"),
        source="MANUAL",
        effective_at=effective_at,
    )

    db_session.add(first)
    await db_session.commit()
    db_session.add(duplicate)

    with pytest.raises(IntegrityError):
        await db_session.commit()


async def test_exchange_rate_rejects_same_currency_pair(db_session: AsyncSession) -> None:
    rate = ExchangeRate(
        base_currency_code="BRL",
        quote_currency_code="BRL",
        rate=Decimal("1"),
        source="MANUAL",
        effective_at=datetime(2026, 7, 1, tzinfo=UTC),
    )
    db_session.add(rate)

    with pytest.raises(IntegrityError):
        await db_session.commit()


async def test_assignor_document_length_is_enforced(db_session: AsyncSession) -> None:
    db_session.add(Assignor(name="Empresa Exemplo", document="123"))

    with pytest.raises(IntegrityError):
        await db_session.commit()


async def test_readiness_reports_database_ok(client: httpx.AsyncClient) -> None:
    response = await client.get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "checks": {"database": "ok"}}
