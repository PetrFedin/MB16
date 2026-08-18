from __future__ import annotations

import asyncio
import io
import json
import logging
from types import SimpleNamespace

import httpx
import pytest
from fastapi import HTTPException

from app import storage, telegram
from scripts import configure_telegram, preflight


class DummyUpload:
    def __init__(self, filename: str, content_type: str, data: bytes):
        self.filename = filename
        self.content_type = content_type
        self.file = io.BytesIO(data)


class FakeS3:
    def __init__(self):
        self.puts: list[dict] = []
        self.deletes: list[dict] = []

    def put_object(self, **kwargs):
        self.puts.append(kwargs)
        return {"ETag": "test"}

    def delete_object(self, **kwargs):
        self.deletes.append(kwargs)
        return {"DeleteMarker": True}


def test_telegram_send_message_contract(monkeypatch):
    calls: list[tuple[str, dict, int]] = []

    class FakeResponse:
        def raise_for_status(self):
            return None

    class FakeClient:
        def __init__(self, timeout: int):
            self.timeout = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, url: str, json: dict):
            calls.append((url, json, self.timeout))
            return FakeResponse()

    monkeypatch.setattr(telegram.settings, "telegram_bot_token", "ci-bot-token")
    monkeypatch.setattr(telegram.httpx, "AsyncClient", FakeClient)

    asyncio.run(telegram.send_telegram_message(123456, "MB16 test"))

    assert calls == [
        (
            "https://api.telegram.org/botci-bot-token/sendMessage",
            {"chat_id": 123456, "text": "MB16 test"},
            8,
        )
    ]


def test_telegram_failure_is_logged_without_raising(monkeypatch, caplog):
    class FailingClient:
        def __init__(self, timeout: int):
            self.timeout = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, url: str, json: dict):
            raise httpx.ConnectError("telegram unavailable")

    monkeypatch.setattr(telegram.settings, "telegram_bot_token", "ci-bot-token")
    monkeypatch.setattr(telegram.httpx, "AsyncClient", FailingClient)
    caplog.set_level(logging.ERROR)

    asyncio.run(telegram.send_telegram_message(123456, "MB16 test"))

    assert "Telegram notification failed for chat_id=123456" in caplog.text


def test_notify_admins_uses_configured_production_ids(monkeypatch):
    sent: list[tuple[int, str]] = []

    async def fake_send(chat_id: int, text: str):
        sent.append((chat_id, text))

    monkeypatch.setattr(telegram.settings, "app_env", "production")
    monkeypatch.setattr(telegram.settings, "admin_telegram_ids", "101,202")
    monkeypatch.setattr(telegram, "send_telegram_message", fake_send)

    asyncio.run(telegram.notify_admins("New fitting"))

    assert {chat_id for chat_id, _ in sent} == {101, 202}
    assert {text for _, text in sent} == {"New fitting"}


def test_s3_upload_public_url_and_cleanup_contract(monkeypatch):
    fake_s3 = FakeS3()
    monkeypatch.setattr(storage.settings, "storage_backend", "s3")
    monkeypatch.setattr(storage.settings, "s3_endpoint_url", "https://s3.example.test")
    monkeypatch.setattr(storage.settings, "s3_access_key_id", "access")
    monkeypatch.setattr(storage.settings, "s3_secret_access_key", "secret")
    monkeypatch.setattr(storage.settings, "s3_bucket", "mb16")
    monkeypatch.setattr(storage.settings, "s3_region", "ru-1")
    monkeypatch.setattr(storage.settings, "s3_public_base_url", "https://cdn.example.test/mb16")
    monkeypatch.setattr(storage, "_s3_client", lambda: fake_s3)
    monkeypatch.setattr(storage.secrets, "token_hex", lambda _: "fixed-key")

    upload = DummyUpload("photo.png", "image/png", b"png-bytes")
    url = storage.save_upload(upload, "image")

    assert url == "https://cdn.example.test/mb16/products/fixed-key.png"
    assert fake_s3.puts == [
        {
            "Bucket": "mb16",
            "Key": "products/fixed-key.png",
            "Body": b"png-bytes",
            "ContentType": "image/png",
        }
    ]

    storage.delete_upload(url)
    assert fake_s3.deletes == [{"Bucket": "mb16", "Key": "products/fixed-key.png"}]


def test_s3_upload_requires_complete_configuration(monkeypatch):
    monkeypatch.setattr(storage.settings, "storage_backend", "s3")
    monkeypatch.setattr(storage.settings, "s3_endpoint_url", "")
    monkeypatch.setattr(storage.settings, "s3_access_key_id", "access")
    monkeypatch.setattr(storage.settings, "s3_secret_access_key", "secret")
    monkeypatch.setattr(storage.settings, "s3_bucket", "mb16")

    with pytest.raises(HTTPException) as error:
        storage.save_upload(DummyUpload("photo.png", "image/png", b"png"), "image")

    assert error.value.status_code == 503
    assert error.value.detail == "S3 storage is not fully configured"


def test_telegram_call_serializes_bot_api_request(monkeypatch):
    captured: dict = {}

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return b'{"ok": true, "result": true}'

    def fake_urlopen(request, timeout: int):
        captured["url"] = request.full_url
        captured["payload"] = json.loads(request.data.decode("utf-8"))
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr(configure_telegram.urllib.request, "urlopen", fake_urlopen)

    result = configure_telegram.telegram_call("test-token", "setChatMenuButton", {"hello": "world"})

    assert result == {"ok": True, "result": True}
    assert captured == {
        "url": "https://api.telegram.org/bottest-token/setChatMenuButton",
        "payload": {"hello": "world"},
        "timeout": 20,
    }


def test_configure_telegram_menu_button_payload(monkeypatch):
    captured: dict = {}

    def fake_call(token: str, method: str, payload: dict):
        captured.update(token=token, method=method, payload=payload)
        return {"ok": True, "result": True}

    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token")
    monkeypatch.setenv("PUBLIC_APP_URL", "https://mb16.example.test/")
    monkeypatch.setattr(configure_telegram, "telegram_call", fake_call)

    configure_telegram.main()

    assert captured == {
        "token": "test-token",
        "method": "setChatMenuButton",
        "payload": {
            "menu_button": {
                "type": "web_app",
                "text": "Открыть шоурум",
                "web_app": {"url": "https://mb16.example.test"},
            }
        },
    }


def test_configure_telegram_rejects_non_https_url(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token")
    monkeypatch.setenv("PUBLIC_APP_URL", "http://mb16.example.test")

    with pytest.raises(SystemExit) as error:
        configure_telegram.main()

    assert "PUBLIC_APP_URL must be an https:// URL" in str(error.value)


def test_production_s3_preflight_requires_all_fields(monkeypatch, capsys):
    settings = SimpleNamespace(
        app_timezone="Europe/Moscow",
        max_image_mb=10,
        max_video_mb=80,
        app_env="production",
        database_url="postgresql+psycopg://user:pass@db:5432/showroom",
        telegram_bot_token="token",
        admin_ids={9001},
        storage_backend="s3",
        s3_endpoint_url="",
        s3_access_key_id="",
        s3_secret_access_key="",
        s3_bucket="",
        s3_public_base_url="",
    )
    monkeypatch.setattr(preflight, "get_settings", lambda: settings)

    with pytest.raises(SystemExit):
        preflight.main()

    output = capsys.readouterr().out
    for name in (
        "S3_ENDPOINT_URL",
        "S3_ACCESS_KEY_ID",
        "S3_SECRET_ACCESS_KEY",
        "S3_BUCKET",
        "S3_PUBLIC_BASE_URL",
    ):
        assert name in output


def test_production_s3_preflight_accepts_complete_configuration(monkeypatch, capsys):
    settings = SimpleNamespace(
        app_timezone="Europe/Moscow",
        max_image_mb=10,
        max_video_mb=80,
        app_env="production",
        database_url="postgresql+psycopg://user:pass@db:5432/showroom",
        telegram_bot_token="token",
        admin_ids={9001},
        storage_backend="s3",
        s3_endpoint_url="https://s3.example.test",
        s3_access_key_id="access",
        s3_secret_access_key="secret",
        s3_bucket="mb16",
        s3_public_base_url="https://cdn.example.test/mb16",
    )
    monkeypatch.setattr(preflight, "get_settings", lambda: settings)

    preflight.main()

    assert "MB16 preflight OK" in capsys.readouterr().out
