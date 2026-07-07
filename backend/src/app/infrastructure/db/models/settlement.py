import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.db.base import Base, CreatedAtMixin


class Settlement(CreatedAtMixin, Base):
    """Immutable record of a batch settlement (audit trail)."""

    __tablename__ = "settlements"
    __table_args__ = (
        CheckConstraint("total_present_value >= 0", name="total_present_value_non_negative"),
        CheckConstraint("total_discount >= 0", name="total_discount_non_negative"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    batch_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("batches.id"), unique=True)
    payment_currency_code: Mapped[str] = mapped_column(ForeignKey("currencies.code"))
    fx_rate: Mapped[Decimal | None] = mapped_column(
        Numeric(20, 10),
        comment="FX rate applied for cross-currency batches (null when same currency)",
    )
    fx_rate_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("exchange_rates.id"), comment="Provenance of the applied FX rate"
    )
    total_face_value: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), comment="Sum of face values, in payment currency"
    )
    total_present_value: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), comment="Sum of present values, in payment currency"
    )
    total_discount: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), comment="Total desagio (face - present), in payment currency"
    )
    settled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    items: Mapped[list["SettlementItem"]] = relationship(
        back_populates="settlement", lazy="raise", cascade="all"
    )


class SettlementItem(CreatedAtMixin, Base):
    """Per-receivable pricing snapshot: every input of the formula is persisted."""

    __tablename__ = "settlement_items"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    settlement_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("settlements.id"), index=True)
    receivable_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("receivables.id"), unique=True)
    face_value: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), comment="Face value in the receivable currency"
    )
    currency_code: Mapped[str] = mapped_column(ForeignKey("currencies.code"))
    base_rate_monthly: Mapped[Decimal] = mapped_column(
        Numeric(10, 6), comment="Base rate snapshot used in the formula"
    )
    spread_monthly: Mapped[Decimal] = mapped_column(
        Numeric(10, 6), comment="Risk spread snapshot used in the formula"
    )
    term_months: Mapped[Decimal] = mapped_column(
        Numeric(10, 4), comment="Term in months (calendar days / 30)"
    )
    present_value: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), comment="Present value in the receivable currency"
    )
    discount_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), comment="Desagio in the receivable currency (face - present)"
    )
    fx_rate: Mapped[Decimal | None] = mapped_column(
        Numeric(20, 10), comment="FX rate applied to this item (null when same currency)"
    )
    present_value_payment: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), comment="Present value converted to the batch payment currency"
    )

    settlement: Mapped[Settlement] = relationship(back_populates="items", lazy="raise")
