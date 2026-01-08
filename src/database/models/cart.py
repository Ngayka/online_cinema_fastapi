from datetime import datetime
from typing import List

from sqlalchemy import Integer, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class Cart(Base):
    __tablename__ = "carts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    user: Mapped["UserModel"] = relationship("UserModel", back_populates="cart")
    items: Mapped[List["CartItem"]] = relationship(
        "CartItem",
        back_populates="cart",
        cascade="all, delete-orphan")


class CartItem(Base):
    __tablename__ = "cart_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    cart_id: Mapped[int] = mapped_column(Integer, ForeignKey("carts.id"), nullable=False)
    movie_id: Mapped[int] = mapped_column(Integer, ForeignKey("movies.id"), nullable=False)
    added_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    cart: Mapped["Cart"] = relationship("Cart", back_populates="items")
    movie: Mapped["MovieModel"] = relationship("MovieModel", back_populates="cart_items")

    __table_args__ = (UniqueConstraint("cart_id", "movie_id"),)
