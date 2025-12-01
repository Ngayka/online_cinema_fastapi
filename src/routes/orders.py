from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from starlette import status

from config import get_settings
from config.dependencies_auth import get_current_user
from database import UserModel, get_db, Cart, CartItem
from schemas import OrderResponseSchema
from config import create_order_service, get_purchased_movie_ids, check_pending_orders
from validation import is_movie_available

router = APIRouter()
app_settings = get_settings()


@router.post(
    "/orders",
    response_model=OrderResponseSchema,
    summary="Add movie to order",
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "Movie added successfully"},
        400: {"description": "Cart is empty"},
        404: {"description": "Movie not found"}
    }
)
async def create_order(
        user: UserModel = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    cart = await db.execute(select(Cart).where(Cart.user_id == user.id)
                            .options(selectinload(Cart.items)
                                     .selectinload(CartItem.movie)))
    cart = cart.scalar_one_or_none()
    if not cart or not cart.items:
        raise HTTPException(status_code=400, detail="Cart is empty")

    purchased_movies = await get_purchased_movie_ids(db, user.id)
    available_cart_items = [
        item for item in cart.items if item.movie_id not in purchased_movies
    ]

    if not available_cart_items:
        raise HTTPException(
            status_code=400, detail="All movies in cart are already purchased"
        )
    unavailable_movies = [
        item.movie.name for item in available_cart_items if not is_movie_available(item.movie)
    ]
    if unavailable_movies:
        raise HTTPException(
            status_code=400, detail=f"Movies not available:','join.{unavailable_movies}"
        )
    movie_ids = [item.movie_id for item in available_cart_items]
    pending_duplicate = await check_pending_orders(db, user_id=user.id, movie_ids=movie_ids)
    if pending_duplicate:
        raise HTTPException(
            status_code=400,
            detail="You already have a pending order with this movie"
        )
    temp_cart = Cart()
    temp_cart.items = available_cart_items
    order = await create_order_service(db=db, cart=temp_cart, user=user)
    return order
