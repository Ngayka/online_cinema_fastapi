from typing import List

from pydantic import BaseModel, field_validator
from datetime import datetime
from decimal import Decimal

from schemas import MovieInCartReadSchema

from database.models.orders import OrderStatusEnum


class OrderItemResponseSchema(BaseModel):
    id: int
    order_id: int
    movie_id: int
    price_at_order: Decimal


class OrderCreateSchema(BaseModel):
    id: int
    movie: list[MovieInCartReadSchema]
    price_at_order: Decimal


class OrderResponseSchema(BaseModel):
    id: int
    created_at: datetime
    total_amount: Decimal
    order_item: List[OrderItemResponseSchema]

    class Config:
        from_attributes = True


class OrderDetailSchema(BaseModel):
    id: int
    created_at: datetime
    order_items: List[OrderCreateSchema]
    total_amount: Decimal
    status: OrderStatusEnum

    class Config:
        from_attributes = True


class OrderListSchema(BaseModel):
    id: int
    created_at: datetime
    total_amount: Decimal
    status: OrderStatusEnum

    class Config:
        from_attributes = True
