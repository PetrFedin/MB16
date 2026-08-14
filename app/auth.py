import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from urllib.parse import parse_qsl

from fastapi import Depends, Header, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import get_settings
from .db import SessionLocal
from .models import User

settings = get_settings()


@dataclass
class AuthIdentity:
    telegram_id: int
    username: str | None
    first_name: str
    last_name: str
    is_admin: bool


def _validate_init_data(init_data: str) -> dict:
    if not settings.telegram_bot_token:
        raise HTTPException(status_code=503, detail="TELEGRAM_BOT_TOKEN is not configured")

    values = dict(parse_qsl(init_data, keep_blank_values=True))
    received_hash = values.pop("hash", "")
    if not received_hash:
        raise HTTPException(status_code=401, detail="Telegram initData has no hash")

    auth_date = int(values.get("auth_date", "0") or 0)
    if auth_date <= 0 or time.time() - auth_date > settings.auth_max_age_seconds:
        raise HTTPException(status_code=401, detail="Telegram initData is expired")

    data_check_string = "\n".join(f"{key}={values[key]}" for key in sorted(values))
    secret_key = hmac.new(b"WebAppData", settings.telegram_bot_token.encode(), hashlib.sha256).digest()
    calculated_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(calculated_hash, received_hash):
        raise HTTPException(status_code=401, detail="Invalid Telegram initData")

    return values


def _identity_from_debug(debug_user: str | None) -> AuthIdentity | None:
    if settings.app_env == "production":
        return None
    if not debug_user:
        return None
    try:
        telegram_id = int(debug_user)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid debug user id") from exc

    if settings.debug_admin_user_id and telegram_id == settings.debug_admin_user_id:
        return AuthIdentity(
            telegram_id=telegram_id,
            username=settings.debug_admin_username,
            first_name=settings.debug_admin_name,
            last_name="",
            is_admin=True,
        )
    return AuthIdentity(
        telegram_id=telegram_id,
        username=settings.debug_telegram_username,
        first_name=settings.debug_telegram_name,
        last_name="",
        is_admin=telegram_id in settings.admin_ids,
    )


def resolve_identity(init_data: str | None, debug_user: str | None) -> AuthIdentity:
    debug_identity = _identity_from_debug(debug_user)
    if debug_identity:
        return debug_identity

    if not init_data:
        if settings.app_env != "production" and settings.debug_telegram_user_id:
            return AuthIdentity(
                telegram_id=settings.debug_telegram_user_id,
                username=settings.debug_telegram_username,
                first_name=settings.debug_telegram_name,
                last_name="",
                is_admin=settings.debug_telegram_user_id in settings.admin_ids,
            )
        raise HTTPException(status_code=401, detail="Open the app from Telegram")

    values = _validate_init_data(init_data)
    try:
        user = json.loads(values.get("user", "{}"))
        telegram_id = int(user["id"])
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=401, detail="Telegram user is missing") from exc

    return AuthIdentity(
        telegram_id=telegram_id,
        username=user.get("username"),
        first_name=user.get("first_name", ""),
        last_name=user.get("last_name", ""),
        is_admin=telegram_id in settings.admin_ids,
    )


def get_or_create_user(db: Session, identity: AuthIdentity) -> User:
    user = db.scalar(select(User).where(User.telegram_id == identity.telegram_id))
    if user is None:
        user = User(
            telegram_id=identity.telegram_id,
            username=identity.username,
            first_name=identity.first_name,
            last_name=identity.last_name,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        changed = False
        for attr, value in (
            ("username", identity.username),
            ("first_name", identity.first_name),
            ("last_name", identity.last_name),
        ):
            if getattr(user, attr) != value:
                setattr(user, attr, value)
                changed = True
        if changed:
            db.commit()
            db.refresh(user)
    return user


def current_context(
    request: Request,
    x_telegram_init_data: str | None = Header(default=None),
    x_debug_user_id: str | None = Header(default=None),
):
    init_data = x_telegram_init_data or request.headers.get("X-Telegram-Init-Data")
    identity = resolve_identity(init_data, x_debug_user_id)
    db = SessionLocal()
    try:
        user = get_or_create_user(db, identity)
        return {"identity": identity, "user_id": user.id, "telegram_id": user.telegram_id}
    finally:
        db.close()


def admin_context(ctx=Depends(current_context)):
    if not ctx["identity"].is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return ctx
