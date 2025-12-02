from decimal import Decimal

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database import Cart, UserModel, Order, OrderItem, OrderStatusEnum


async def create_order_service(db: AsyncSession, cart: Cart, user: UserModel) -> Order:
    total_amount = Decimal("0")
    for cart_item in cart.items:
        total_amount += cart_item.movie.current_price

    order = Order(
        user_id=user.id,
        status=OrderStatusEnum.PENDING,
        total_amount=total_amount
    )

    db.add(order)
    await db.commit()
    await db.refresh(order)

    for cart_item in cart.items:
        order_item = OrderItem(
            order_id=order.id,
            movie_id=cart_item.movie_id,
            price_at_order=cart_item.movie.current_price
        )
        db.add(order_item)
    await db.commit()

    result = await db.execute(select(Order)
                        .where(Order.id == order.id)
                        .options(
                            selectinload(Order.order_items).
                            selectinload(OrderItem.movie)
        )
    )
    return result.scalar_one()


async def check_pending_orders(db: AsyncSession, user_id: int, movie_ids: list[int]) -> bool:
    result = db.execute(select(OrderItem)
                        .join(Order)
                        .where(
                            Order.user_id == user_id,
                            Order.status == OrderStatusEnum.PENDING,
                            OrderItem.movie_id.in_(movie_ids)
        )
    )
    return result.scalars().one() or None


async def get_purchased_movie_ids(db: AsyncSession, user_id: int) -> set[int]:
    result = db.execute(select(OrderItem.movie_id).join(Order).where(Order.user_id == user_id,
                                                                     Order.status == OrderStatusEnum.PAID))

    return {row[0] for row in result.all()}


async def get_order_by_id_and_user(order_id: int, db: AsyncSession, user: UserModel):
    result = await db.execute(select(Order)
    .where(
        Order.user_id == user.id,
        Order.id == order_id
    )
    .options(
        selectinload(Order.order_items)
        .selectinload(OrderItem.movie)
    )
    )
    return result or None
