import asyncio

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from starlette import status

from config import get_settings, get_order_by_id_and_user
from config.dependencies_auth import get_current_user
from notifications import EmailSenderInterface
from database import (
    UserModel,
    get_db,
    Cart,
    CartItem,
    Order,
    OrderItem,
    OrderStatusEnum,
    PaymentItem,
    Payment,
    PaymentStatusEnum
)

from schemas import (OrderResponseSchema,
                     OrderListSchema,
                     OrderDetailSchema,
                     MessageResponseSchema,
                     PaymentRequestSchema)
from services import process_payment
from config import create_order_service, get_purchased_movie_ids, check_pending_orders
from validation import is_movie_available, validate_payment_method

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


@router.get(
    "/orders/me",
    response_model=OrderListSchema,
    summary="Return all user`s orders",
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "All orders retrieved successfully"},
        404: {"description": "Orders not found"}
    }
)
async def return_all_orders(user: UserModel = Depends(get_current_user),
                            db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Order)
                              .where(Order.user_id == user.id)
                              )
    orders = result.scalars().all()
    if not orders:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Orders not found")
    return orders


@router.get(
    "/orders/{order_id}",
    response_model=OrderDetailSchema,
    summary="Return order detail",
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "Order retrieve successfully"},
        404: {"description": "Order not found"}
    }
)
async def return_order_by_id(
        order_id: int,
        user: UserModel = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
):
    result = await get_order_by_id_and_user(order_id, db, user)
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Order not found")
    return order


@router.post(
    "/orders/{order_id}/cancel",
    response_model=MessageResponseSchema,
    summary="Cancel order by id",
    description="Cancel order by id, if order status is pending",
    status_code=status.HTTP_200_OK
)
async def cancel_order(order_id: int,
                       db: AsyncSession = Depends(get_db),
                       user: UserModel = Depends(get_current_user)) -> MessageResponseSchema:
    result = await get_order_by_id_and_user(order_id, db, user)
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Order not found")
    if order.status != OrderStatusEnum.PENDING:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"You can`t cancel order with status: {order.status}. "
                                   f"Only pending orders can be cancelled")
    order.status = OrderStatusEnum.CANCELED
    await db.commit()

    return MessageResponseSchema(
        message=f"Order {order_id} have been successfully cancelled"
    )


@router.post(
    "orders/{order_id}/pay",
    response_model=OrderResponseSchema,
    summary="Process order payment",
    description="Process payment for an order and update its status to PAID",
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "Payment processed successfully"},
        400: {"description": "Cannot process payment"},
        404: {"description": "Order not found"},
        402: {"description": "Payment failed"}
    }
)
async def pay_order(order_id: int,
                    payment_data: PaymentRequestSchema,
                    db: AsyncSession = Depends(get_db),
                    user: UserModel = Depends(get_current_user),
                    email_sender: EmailSenderInterface = Depends(send_payment_confirmation_email)
                    ):
    """
        Process payment for an order

        Steps:
        1. Validate order exists and belongs to user
        2. Check order is in PENDING status
        3. Validate payment data
        4. Process payment through payment gateway
        5. Update order status to PAID
        6. Send confirmation email
        """
    result = await get_order_by_id_and_user(order_id, db, user)
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    if order.status != OrderStatusEnum.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"You can`t pay order with status: {order.status}. "
                   f"Only pending orders can be paid")

    await validate_payment_method(payment_data)

    try:
        payment_result = await process_payment(order, payment_data, user)
        if not payment_result["success"]:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail={
                    "message": payment_result["message"],
                    "error": payment_result.get("error"),
                    "suggestion": payment_result.get("suggestion")
                }
            )
        order.status = OrderStatusEnum.PAID
        payment = Payment(
            user_id=user.id,
            order_id=order.id,
            amount=order.total_amount,
            status=PaymentStatusEnum.SUCCESSFUL,
            external_payment_id=payment_result["transaction_id"]
        )
        db.add(payment)

        for order_item in order.order_items:
            payment_item = PaymentItem(
                payment_id=payment.id,
                order_item_id=order_item.id,
                price_at_payment=order_item.price_at_order
            )
            db.add(payment_item)
        await db.commit()
        asyncio.create_task(
            send_payment_confirmation_email
        )
