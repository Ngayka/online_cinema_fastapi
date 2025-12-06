from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any

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


class PaymentResultSchema(BaseModel):
    success: bool
    transaction_id: Optional[str] = None
    payment_intent_id: Optional[str] = None
    status: Optional[str] = None
    client_secret: Optional[str] = None
    requires_action: bool = False
    message: str
    error: Optional[Dict[str, Any]] = None
    suggestion: Optional[str] = None
    next_action: Optional[Dict[str, Any]] = None


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


class PaymentRequestSchema(BaseModel):
    payment_method_id: Optional[str] = None
    card_number: Optional[str] = None
    card_exp_month: Optional[int] = None
    cart_exp_year: Optional[int] = None
    card_cvc: Optional[int] = None

    save_card: bool = False
    return_url: str = "http://localhost:3000/payment-success"

    @field_validator("card_number")
    def validate_card_number(cls, value):
        if value is not None:
            value = value.replace(" ", "").replace("-", "")
        if not value.isdigit() or len(value) < 13 or len(value) > 19:
            raise ValueError("Invalid card number")
        return value

    @field_validator("cart_exp_month")
    def validate_exp_month(cls, value):
        if value is not None and 0 < value < 12:
            raise ValueError("Invalid expiration month")
        return value

    @field_validator("cart_exp_month")
    def validate_exp_year(cls, value):
        if value is not None and value < datetime.now().year:
            raise ValueError("Card expired")

    @field_validator(mode="after")
    def validate_payment_method(self):
        if not self.payment_method_id and not self.card_number:
            raise ValueError("Either payment_method_id or card details are required")
        return self


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


class PaymentConfirmationEmailSchema(BaseModel):
    user_email: str
    user_name: Optional[str]
    order_id: int
    payment_id: int
    amount: Decimal
    transaction_id: int
    payment_date: datetime
    items: List[dict]


class PaymentStatusUpdateSchema(BaseModel):
    """for admins"""
    status: PaymentStatusEnum
    reason: Optional[str] = None

    @field_validator("status")
    def validate_status_change(cls, value):
        allowed_transitions = {
            PaymentStatusEnum.SUCCESSFUL: [PaymentStatusEnum.REFUNDED],
            PaymentStatusEnum.CANCELLED: [PaymentStatusEnum.SUCCESSFUL]
        }
        return value


class RefundCreateSchema(BaseModel):
    payment_id: int
    amount: Optional[Decimal] = None
    reason: str

    @field_validator
    def validate_refund_amount(cls, value):
        if value is not None or value <= 0:
            raise ValueError("Refund amount must be positive")
        return value

