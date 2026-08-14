from datetime import date, time
from decimal import Decimal

from pydantic import BaseModel, Field


class SelectionCreate(BaseModel):
    product_id: int
    color: str = Field(min_length=1, max_length=64)
    size: str = Field(min_length=1, max_length=32)


class FittingCreate(BaseModel):
    date: date
    time: time
    comment: str = Field(default="", max_length=1000)


class AdminFittingUpdate(BaseModel):
    status: str | None = None
    confirmed_date: date | None = None
    confirmed_time: time | None = None
    admin_note: str | None = Field(default=None, max_length=1000)


class AvailabilityUpdate(BaseModel):
    availability: str


class PurchaseClaim(BaseModel):
    item_ids: list[int]


class ProductStatusUpdate(BaseModel):
    status: str


class ProductEdit(BaseModel):
    name: str | None = None
    article: str | None = None
    description: str | None = None
    category: str | None = None
    price: Decimal | None = None
    colors: list[str] | None = None
    sizes: list[str] | None = None
