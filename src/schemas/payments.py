from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, field_validator

from database.models.payments import PaymentStatusEnum
from schemas import OrderListSchema, MovieInCartReadSchema


class PaymentCreateSchema(BaseModel):
    order_id: int
    payment_method: str = "card"
    save_card: bool = False


class StripeCreateSchema(PaymentCreateSchema):
    stripe_token: Optional[str] = None
    return_url: str


class PaymentResponseSchema(BaseModel):
    int: int
    order_id: int
    amount: Decimal
    status: PaymentStatusEnum
    created_at: datetime
    payment_url: Optional[str]
    client_secret: Optional[str]

    class Config:
        from_attributes = True


class PaymentListSchema(BaseModel):
    id: int
    order_id: int
    amount: Decimal
    status: PaymentStatusEnum
    created_at: datetime

    class Config:
        from_attributes = True


class PaymentDetailSchema(BaseModel):
    id: int
    order_id: int
    amount: Decimal
    status: PaymentStatusEnum
    created_at: datetime
    external_payment_id: Optional[str]

    order: OrderListSchema

    payment_items: list["PaymentItemSchema"]

    class Config:
        from_attributes = True


class PaymentItemSchema(BaseModel):
    id: int
    payment_id: int
    order_item_id: int
    price_at_payment: Decimal

    movie: MovieInCartReadSchema

    class Config:
        from_attributes = True


class PaymentFilterSchema(BaseModel):
    """Admin Options"""
    user_id: Optional[int] = None
    status: Optional[PaymentStatusEnum] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    min_amount: Optional[Decimal] = None
    max_amount: Optional[Decimal] = None

    @field_validator("end_date")
    def validate_dates(cls, value, info):
        if "start_date" in info.data and value and info.data["start_date"]:
            if value < info.data["start_date"]:
                raise ValueError("End date must be after start date")
            return value


class StripeWebhookSchema(BaseModel):
    id: str
    type: str
    data: dict
    created: int

    class Config:
        extra = "allow"


class PaymentErrorSchema(BaseModel):
    error: str
    code: str
    suggestion: Optional[str] = None
    retry_allowed: bool = True


class PaymentSuccessSchema(BaseModel):
    message: str
    order_id: int
    payment_is: int
    amount: Decimal
    transaction_id: int
    paid_at: datetime


class PaymentConfirmationEmailSchema
