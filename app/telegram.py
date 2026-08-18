import logging

import httpx

from .config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


async def send_telegram_message(chat_id: int, text: str) -> None:
    if not settings.telegram_bot_token:
        return
    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            response = await client.post(url, json={"chat_id": chat_id, "text": text})
            response.raise_for_status()
    except httpx.HTTPError:
        logger.exception("Telegram notification failed for chat_id=%s", chat_id)


async def notify_admins(text: str) -> None:
    for admin_id in settings.admin_ids:
        await send_telegram_message(admin_id, text)
