from typing import Optional

from fastapi import HTTPException

from database import UserModel, Order
from schemas import PaymentRequestSchema


def validate_payment_method(
    payment_data: PaymentRequestSchema,
    user: Optional[UserModel],
    order: Optional[Order],
):
    if not payment_data.payment_method_id:
        raise HTTPException(status_code=400, detail="Payment method required")
    if order and order.total_amount <= 0:
        raise HTTPException(status_code=400, detail="Invalid order amount")
    if user and not user.is_active:
        raise HTTPException(status_code=400, detail="User is not active")
