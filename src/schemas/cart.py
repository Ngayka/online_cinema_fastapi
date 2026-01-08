from datetime import datetime

from pydantic import BaseModel


class MovieInCartReadSchema(BaseModel):
    id: int
    name: str
    score: float


class CartItemCreateSchema(BaseModel):
    movie_id: int


class CartItemReadSchema(BaseModel):
    id: int
    movie: MovieInCartReadSchema
    added_at: datetime

    class Config:
        orm_mode = True


class CartReadSchema(BaseModel):
    id: int
    items: list[CartItemReadSchema]

    class Config:
        orm_mode = True
