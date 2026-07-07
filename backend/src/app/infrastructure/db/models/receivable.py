import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.enums import BatchStatus
from app.infrastructure.db.base import Base, CreatedAtMixin


class ReceivableType(CreatedAtMixin, Base):
    __tablename__ = "receivable_types"
    __table_args__ = (CheckConstraint("monthly_spread >= 0", name="monthly_spread_non_negative"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(30), unique=True, comment="DUPLICATA, CHEQUE, ...")
    name: Mapped[str] = mapped_column(String(80))
    monthly_spread: Mapped[Decimal] = mapped_column(
        Numeric(10, 6), comment="Risk spread per month as a decimal fraction (0.015 = 1.5% p.m.)"
    )
    active: Mapped[bool] = mapped_column(default=True)


class Assignor(CreatedAtMixin, Base):
    __tablename__ = "assignors"
    __table_args__ = (CheckConstraint("char_length(document) = 14", name="document_length"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(120))
    document: Mapped[str] = mapped_column(String(14), unique=True, comment="CNPJ (digits only)")


class Batch(Base):
    __tablename__ = "batches"
    __table_args__ = (
        CheckConstraint("status IN ('PENDING', 'SETTLED')", name="status_valid"),
        CheckConstraint("version >= 1", name="version_positive"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    assignor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("assignors.id"), index=True)
    payment_currency_code: Mapped[str] = mapped_column(ForeignKey("currencies.code"))
    status: Mapped[str] = mapped_column(String(20), default=BatchStatus.PENDING)
    version: Mapped[int] = mapped_column(default=1, comment="Optimistic locking token")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    receivables: Mapped[list["Receivable"]] = relationship(
        back_populates="batch", lazy="raise", cascade="all"
    )


class Receivable(CreatedAtMixin, Base):
    __tablename__ = "receivables"
    __table_args__ = (CheckConstraint("face_value > 0", name="face_value_positive"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    batch_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("batches.id"), index=True)
    receivable_type_id: Mapped[int] = mapped_column(ForeignKey("receivable_types.id"))
    face_value: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), comment="Face value in the receivable currency"
    )
    currency_code: Mapped[str] = mapped_column(ForeignKey("currencies.code"))
    due_date: Mapped[date] = mapped_column(Date)

    batch: Mapped[Batch] = relationship(back_populates="receivables", lazy="raise")
