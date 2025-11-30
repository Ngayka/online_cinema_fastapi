from pydantic import BaseModel, field_validator
from datetime import datetime
from decimal import Decimal

from schemas import MovieInCartReadSchema

from database.models.orders import StatusEnum


class OrderCreateSchema(BaseModel):
    id: int
    movie: list[MovieInCartReadSchema]
    price_at_order: Decimal


class OrderDetailSchema(BaseModel):
    id: int
    created_at: datetime
    order_item: list[OrderCreateSchema]
    total_amount: Decimal
    status: StatusEnum

    class Config:
        from_attributes = True


class OrderListSchema(BaseModel):
    id: int
    created_at: datetime
    total_amount: Decimal
    status: StatusEnum

    class Config:
        from_attributes = True
