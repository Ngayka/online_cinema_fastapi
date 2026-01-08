import enum
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Integer, ForeignKey, DateTime, Enum, DECIMAL
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class OrderStatusEnum(str, enum.Enum):
    PENDING = "pending"
    PAID = "paid"
    CANCELED = "canceled"


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    status: Mapped[OrderStatusEnum] = mapped_column(Enum(OrderStatusEnum), nullable=False, default=OrderStatusEnum.PENDING)
    total_amount: Mapped[Decimal] = mapped_column(DECIMAL(10, 2), nullable=True)

    order_items: Mapped[list["OrderItem"]] = relationship(back_populates="order")
    user: Mapped["UserModel"] = relationship(back_populates="orders")
    payment: Mapped[list["Payment"]] = relationship("Payment", back_populates="order")


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(Integer, ForeignKey("orders.id"), nullable=False)
    movie_id: Mapped[int] = mapped_column(Integer, ForeignKey("movies.id"), nullable=False)
    price_at_order: Mapped[Decimal] = mapped_column(DECIMAL(10, 2), nullable=False)

    order: Mapped["Order"] = relationship(back_populates="order_items")
    movie: Mapped["MovieModel"] = relationship(back_populates="order_items")
    payment_items: Mapped[list["PaymentItem"]] = relationship("PaymentItem", back_populates="order_items")
