import enum
from datetime import datetime
from decimal import Decimal
from typing import Optional, List

from sqlalchemy import Integer, ForeignKey, DateTime, DECIMAL, Enum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base, UserModel, Order


class PaymentStatusEnum(str, enum.Enum):
    SUCCESSFUL = "successful"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    order_id: Mapped[int] = mapped_column(Integer, ForeignKey("orders.id"), nullable=False)
    status: Mapped[PaymentStatusEnum] = mapped_column(Enum(PaymentStatusEnum), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    amount: Mapped[Decimal] = mapped_column(DECIMAL(10, 2), nullable=False)
    external_payment_id:  Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    user: Mapped["UserModel"] = relationship(back_populates="payments")
    order: Mapped["Order"] = relationship(back_populates="payment")
    payment_items: Mapped[list["PaymentItem"]] = relationship(back_populates="payment")


class PaymentItem(Base):
    __tablename__ = "payment_items"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    payment_id: Mapped[int] = mapped_column(Integer, ForeignKey("payments.id"))
    order_item_id: Mapped[int] = mapped_column(Integer, ForeignKey("order_items.id"))
    price_at_payment: Mapped[Decimal] = mapped_column(DECIMAL(10, 2), nullable=False)

    payment: Mapped["Payment"] = relationship(back_populates="payment_items")
    order: Mapped["Order"] = relationship(back_populates="payment_items")
