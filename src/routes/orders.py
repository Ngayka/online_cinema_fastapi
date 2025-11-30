from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from starlette import status

from config import get_settings
from config.dependencies_auth import get_current_user
from database import UserModel, get_db, Cart, CartItem
from schemas import OrderCreateSchema

router = APIRouter()
app_settings = get_settings()


@router.post(
    "/orders/",
    response_model=OrderCreateSchema,
    summary="Add movie to order",
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "Movie added successfully"},
        400: {"description": "Movie already in cart"},
        404: {"description": "Movie not found"}
    }
)
async def create_order(
        user: UserModel = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    cart = await db.execute(select(Cart).where(Cart.user_id == user.id)
                            .options(selectinload(Cart.item)
                                     .selectinload(CartItem.movie)))
    cart = cart.scalar_one_or_none()
