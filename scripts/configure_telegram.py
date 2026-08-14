"""Configure the bot menu button to open the deployed MB16 Mini App."""

from __future__ import annotations

import json
import os
import urllib.request


def telegram_call(token: str, method: str, payload: dict) -> dict:
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/{method}",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    app_url = os.environ.get("PUBLIC_APP_URL", "").strip().rstrip("/")
    if not token:
        raise SystemExit("TELEGRAM_BOT_TOKEN is required")
    if not app_url.startswith("https://"):
        raise SystemExit("PUBLIC_APP_URL must be an https:// URL")

    menu = telegram_call(token, "setChatMenuButton", {
        "menu_button": {
            "type": "web_app",
            "text": "Открыть шоурум",
            "web_app": {"url": app_url},
        }
    })
    if not menu.get("ok"):
        raise SystemExit(f"setChatMenuButton failed: {menu}")

    print("Telegram Mini App menu button configured")


if __name__ == "__main__":
    main()
