from typing import List

from pydantic import BaseModel, field_validator, ConfigDict
from datetime import datetime
from decimal import Decimal

from schemas import MovieInCartReadSchema

from database.models.orders import OrderStatusEnum


class OrderItemResponseSchema(BaseModel):
    id: int
    order_id: int
    movie_id: int
    price_at_order: Decimal

    model_config = ConfigDict(from_attributes=True)


class OrderItemWithMovieSchema(BaseModel):
    id: int
    movie: MovieInCartReadSchema
    price_at_order: Decimal


class OrderResponseSchema(BaseModel):
    id: int
    created_at: datetime
    total_amount: Decimal
    order_items: List[OrderItemResponseSchema]

    model_config = ConfigDict(from_attributes=True)


class OrderDetailSchema(BaseModel):
    id: int
    created_at: datetime
    order_items: List[OrderItemWithMovieSchema]
    total_amount: Decimal
    status: OrderStatusEnum

    class Config:
        from_attributes = True


class OrderListSchema(BaseModel):
    orders: list[OrderResponseSchema]

    class Config:
        from_attributes = True
