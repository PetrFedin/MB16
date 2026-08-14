from __future__ import annotations

from datetime import date, datetime, time, timezone
from decimal import Decimal

from sqlalchemy import BigInteger, Boolean, Date, DateTime, ForeignKey, Integer, JSON, Numeric, String, Text, Time, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    first_name: Mapped[str] = mapped_column(String(128), default="")
    last_name: Mapped[str] = mapped_column(String(128), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(180))
    description: Mapped[str] = mapped_column(Text, default="")
    article: Mapped[str] = mapped_column(String(96), unique=True, index=True)
    category: Mapped[str] = mapped_column(String(64), default="Одежда")
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    colors: Mapped[list[str]] = mapped_column(JSON, default=list)
    sizes: Mapped[list[str]] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(24), default="available", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    media: Mapped[list[ProductMedia]] = relationship(back_populates="product", cascade="all, delete-orphan", order_by="ProductMedia.sort_order")


class ProductMedia(Base):
    __tablename__ = "product_media"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), index=True)
    media_type: Mapped[str] = mapped_column(String(16))
    url: Mapped[str] = mapped_column(Text)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    product: Mapped[Product] = relationship(back_populates="media")


class SelectionItem(Base):
    __tablename__ = "selection_items"
    __table_args__ = (UniqueConstraint("user_id", "product_id", "selected_color", "selected_size", name="uq_selection_variant"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), index=True)
    selected_color: Mapped[str] = mapped_column(String(64))
    selected_size: Mapped[str] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    product: Mapped[Product] = relationship()


class FittingRequest(Base):
    __tablename__ = "fitting_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    requested_date: Mapped[date] = mapped_column(Date)
    requested_time: Mapped[time] = mapped_column(Time)
    confirmed_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    confirmed_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    comment: Mapped[str] = mapped_column(Text, default="")
    admin_note: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(24), default="new", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    user: Mapped[User] = relationship()
    items: Mapped[list[FittingItem]] = relationship(back_populates="request", cascade="all, delete-orphan")


class FittingItem(Base):
    __tablename__ = "fitting_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    request_id: Mapped[int] = mapped_column(ForeignKey("fitting_requests.id", ondelete="CASCADE"), index=True)
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id", ondelete="SET NULL"), nullable=True, index=True)
    product_name: Mapped[str] = mapped_column(String(180))
    article: Mapped[str] = mapped_column(String(96))
    price_snapshot: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    selected_color: Mapped[str] = mapped_column(String(64))
    selected_size: Mapped[str] = mapped_column(String(32))
    availability: Mapped[str] = mapped_column(String(24), default="pending")
    purchased_claimed: Mapped[bool] = mapped_column(Boolean, default=False)
    sold_confirmed: Mapped[bool] = mapped_column(Boolean, default=False)

    request: Mapped[FittingRequest] = relationship(back_populates="items")
    product: Mapped[Product | None] = relationship()
