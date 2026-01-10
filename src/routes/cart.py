from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from config import get_settings
from config.dependencies_auth import get_current_user
from database import get_db, Cart, CartItem, UserModel, MovieModel
from schemas import (
    CartReadSchema,
    CartItemCreateSchema,
    CartItemReadSchema,
    MovieInCartReadSchema,
)


router = APIRouter()
app_settings = get_settings()


@router.get(
    "/me",
    response_model=CartReadSchema,
    summary="User`s cart",
    description="Get all movies in user`s cart",
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "Cart retrieved successfully"},
        401: {"description": "Unauthorized"},
    },
)
async def get_cart(
    user: UserModel = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> CartReadSchema:
    """
    Retrieve the authenticated user's cart.

    The endpoint returns the user's cart with all items (movies).
    If the user has no cart, or it is empty, an empty cart structure is returned.

    Args:
        user (UserModel): The currently authenticated user.
        db (AsyncSession): Database session dependency.

    Returns:
        CartReadSchema: The user's cart with a list of cart items.
    """
    result = await db.execute(
        select(Cart)
        .where(Cart.user_id == user.id)
        .options(selectinload(Cart.items).selectinload(CartItem.movie))
    )
    cart = result.scalar_one_or_none()

    if not cart:
        return CartReadSchema(id=0, items=[])
    cart_items = cart.items
    if not isinstance(cart_items, list):
        cart_items = [cart_items] if cart_items else []

    items = [
        CartItemReadSchema(
            id=item.id,
            movie=MovieInCartReadSchema(
                id=item.movie.id, name=item.movie.name, score=item.movie.score
            ),
            added_at=item.added_at,
        )
        for item in cart_items
    ]

    return CartReadSchema(id=cart.id, items=items)


@router.post(
    "/items",
    response_model=CartItemReadSchema,
    summary="Add film to cart",
    description="Add new movie to user`s cart",
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "Movie added successfully"},
        400: {"description": "Movie already in cart"},
        404: {"description": "Movie not found"},
    },
)
async def add_movie_to_cart(
    cart_item: CartItemCreateSchema,
    user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Add a movie to the authenticated user's cart.

    Validates that the movie exists and is not already in the user's cart.
    Creates a CartItem entry linking the user's cart and the selected movie.

    Args:
        cart_item (CartItemCreateSchema): Payload containing the movie ID.
        user (UserModel): The currently authenticated user.
        db (AsyncSession): Database session dependency.

    Returns:
        CartItemReadSchema: The created cart item with movie information.

    Raises:
        HTTPException: If the movie does not exist (404) or is already in cart (400).
    """
    result = await db.execute(select(Cart).where(Cart.user_id == user.id))
    cart = result.scalar_one_or_none()

    if not cart:
        cart = Cart(user_id=user.id)
        db.add(cart)
        await db.commit()
        result = await db.execute(
            select(Cart).where(Cart.id == cart.id).options(selectinload(Cart.items))
        )
        cart = result.scalar_one()

    result = await db.execute(
        select(MovieModel).where(MovieModel.id == cart_item.movie_id)
    )
    movie = result.scalars().first()
    if not movie:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Movie not found"
        )

    result = await db.execute(
        select(CartItem).where(
            CartItem.cart_id == cart.id, CartItem.movie_id == movie.id
        )
    )
    existing_item = result.scalars().first()
    if existing_item:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Movie already in cart"
        )

    new_item = CartItem(cart_id=cart.id, movie_id=movie.id)

    db.add(new_item)
    await db.commit()
    await db.refresh(new_item, ["movie"])
    return CartItemReadSchema(
        id=new_item.id,
        movie=MovieInCartReadSchema(
            id=new_item.movie.id, name=new_item.movie.name, score=new_item.movie.score
        ),
        added_at=new_item.added_at,
    )


@router.delete(
    "/items/{item_id}",
    summary="Delete a movie from cart by id",
    description="Delete a specific movie from the cart by its unique ID.",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        204: {"description": "Movie successfully deleted from cart"},
        404: {"description": "Movie not in cart"},
    },
)
async def delete_movie_from_cart(
    item_id: int,
    db: AsyncSession = Depends(get_db),
    user: UserModel = Depends(get_current_user),
) -> None:
    """
    Delete a specific movie from the authenticated user's cart.

    The endpoint removes a cart item by its ID, ensuring that it belongs
    to the current user's cart.

    Args:
        item_id (int): ID of the cart item to delete.
        db (AsyncSession): Database session dependency.
        user (UserModel): The currently authenticated user.

    Returns:
        None

    Raises:
        HTTPException: If the cart item is not found in the user's cart (404).
    """
    result = await db.execute(select(Cart).where(Cart.user_id == user.id))
    cart = result.scalar_one_or_none()

    if not cart:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Cart not found"
        )

    result = await db.execute(
        select(CartItem).where(CartItem.id == item_id, CartItem.cart_id == cart.id)
    )
    cart_item = result.scalar_one_or_none()
    if not cart_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Movie not in cart"
        )
    await db.delete(cart_item)
    await db.commit()
    return None


@router.delete(
    "/items/",
    summary="Delete all movies from cart",
    description="Delete all movies from the cart by its unique ID.",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        204: {"description": "All movies successfully deleted from cart"},
        404: {"description": "No movies in the cart"},
    },
)
async def delete_all_movies(
    db: AsyncSession = Depends(get_db), user: UserModel = Depends(get_current_user)
) -> None:
    """
    Delete all movies from the authenticated user's cart.

    The endpoint removes all CartItem entries belonging to the user's cart.
    If the cart is already empty, an error is returned.

    Args:
        db (AsyncSession): Database session dependency.
        user (UserModel): The currently authenticated user.

    Returns:
        None

    Raises:
        HTTPException: If the cart contains no items (404).
    """
    stmt = select(Cart.id).where(Cart.user_id == user.id)
    result = await db.execute(stmt)
    cart_id = result.scalar()
    if not cart_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No movies in the cart"
        )
    await db.execute(delete(CartItem).where(CartItem.cart_id == cart_id))
    await db.commit()
    return None
