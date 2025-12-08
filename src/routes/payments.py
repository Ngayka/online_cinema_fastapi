import asyncio
from decimal import Decimal
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from starlette import status

from config import get_settings, get_order_by_id_and_user, get_accounts_email_notificator, get_payment_service
from config.dependencies_auth import get_current_user
from database import (
    UserModel,
    get_db, Payment)
from schemas import PaymentListSchema, PaymentDetailSchema

router = APIRouter()
app_settings = get_settings()


@router.get("/payments",
            response_model=List[PaymentListSchema],
            summary="Add user`s payment history",
            status_code=status.HTTP_200_OK,
            responses={
                200: {"description": "Payment history retrieved successfully"},
                401: {"description": "Unauthorized"},
                400: {"description": "No payments history"}
            }
            )
async def get_all_users_payment(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=50, description="Payments per page"),
    user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
        Get payment history for current user with pagination

        - page: number of page(begin from 1)
        - per_page: number of payments by page
        Returns list of payments ordered by creation date (newest first)
        """
    skip = (page - 1) * per_page
    query = (
        select(Payment)
        .where(Payment.user_id == user.id)
        .order_by(Payment.created_at.desc())
        .offset(skip)
        .limit(per_page)
    )
    result = await db.execute(query)

    payments = result.scalars().all()
    if not payments and page == 1:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="No payments history")
    return payments


@router.get("/payments/{payment_id}",
            response_model=PaymentDetailSchema,
            summary="Get payment details",
            status_code=status.HTTP_200_OK,
            responses={
                200: {"descriptions": "Payment order detail retrieved successfully"},
                400: {"descriptions": "Invalid payment ID"},
                401: {"description": "Unauthorized"},
                404: {"description": "Payment not found or access denied"}
            }
            )
async def get_payment_by_id(
        payment_id: Query(..., ge=1, description="Payment ID"),
        user: UserModel = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    """
        Get detailed information about a specific payment

        Parameters:
        - **payment_id**: ID of the payment to retrieve

        Returns payment details including payment items
        """
    query = (select(Payment)
            .where(
                Payment.user_id == user.id,
                Payment.id == payment_id
        )
        .options(selectinload(Payment.payment_items)
        ))

    result = await db.execute(query)
    payment = result.scalar_one_or_none()
    if not payment:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Payment not found or you don't have access to it")
    return payment

