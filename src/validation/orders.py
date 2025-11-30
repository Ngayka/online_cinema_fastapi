from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import MovieModel
from database.models.movies import MovieStatusEnum
from database.models.orders import OrderItem, Order, OrderStatusEnum


async def is_movie_available(movie: MovieModel) -> bool:
    return movie.is_active and movie.status == MovieStatusEnum.RELEASED


async def get_purchased_movie_ids(db: AsyncSession, user_id: int) -> set[int]:
    result = db.execute(select(OrderItem.movie_id).join(Order).where(Order.user_id == user_id,
                                                                     Order.status == OrderStatusEnum.PAID))

    return {row[0] for row in result.all()}


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
