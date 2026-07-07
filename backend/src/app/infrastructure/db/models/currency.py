import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    SmallInteger,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.db.base import Base, CreatedAtMixin


class Currency(CreatedAtMixin, Base):
    __tablename__ = "currencies"

    code: Mapped[str] = mapped_column(String(3), primary_key=True, comment="ISO 4217 code")
    name: Mapped[str] = mapped_column(String(50))
    decimal_places: Mapped[int] = mapped_column(
        SmallInteger, default=2, comment="Rounding precision for monetary amounts"
    )


class ExchangeRate(CreatedAtMixin, Base):
    __tablename__ = "exchange_rates"
    __table_args__ = (
        CheckConstraint("rate > 0", name="rate_positive"),
        CheckConstraint("base_currency_code <> quote_currency_code", name="distinct_currencies"),
        UniqueConstraint("base_currency_code", "quote_currency_code", "effective_at"),
        Index(
            "ix_exchange_rates_pair_effective",
            "base_currency_code",
            "quote_currency_code",
            "effective_at",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    base_currency_code: Mapped[str] = mapped_column(ForeignKey("currencies.code"))
    quote_currency_code: Mapped[str] = mapped_column(ForeignKey("currencies.code"))
    rate: Mapped[Decimal] = mapped_column(
        Numeric(20, 10), comment="Units of quote currency per 1 unit of base currency"
    )
    source: Mapped[str] = mapped_column(String(30), comment="MANUAL or MOCK_PROVIDER")
    effective_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), comment="Moment from which this rate is valid"
    )


class BaseRate(CreatedAtMixin, Base):
    __tablename__ = "base_rates"
    __table_args__ = (
        CheckConstraint("monthly_rate >= 0", name="monthly_rate_non_negative"),
        UniqueConstraint("currency_code", "effective_at"),
        Index("ix_base_rates_currency_effective", "currency_code", "effective_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    currency_code: Mapped[str] = mapped_column(ForeignKey("currencies.code"))
    monthly_rate: Mapped[Decimal] = mapped_column(
        Numeric(10, 6), comment="Monthly base rate as a decimal fraction (0.01 = 1% p.m.)"
    )
    effective_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), comment="Moment from which this rate is valid"
    )
