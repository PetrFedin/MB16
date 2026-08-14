import httpx

from .config import get_settings

settings = get_settings()


async def send_telegram_message(chat_id: int, text: str) -> None:
    if not settings.telegram_bot_token:
        return
    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            await client.post(url, json={"chat_id": chat_id, "text": text})
    except httpx.HTTPError:
        return


async def notify_admins(text: str) -> None:
    for admin_id in settings.admin_ids:
        await send_telegram_message(admin_id, text)
