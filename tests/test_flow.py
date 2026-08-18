import base64
import hashlib
import hmac
import json
import os
import sys
import time
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import urlencode

import pytest
from fastapi import HTTPException

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL", "").strip()
if TEST_DATABASE_URL:
    os.environ["DATABASE_URL"] = TEST_DATABASE_URL
else:
    TEST_DB = Path("/tmp/mb16-test.db")
    if TEST_DB.exists():
        TEST_DB.unlink()
    os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB}"
os.environ["APP_ENV"] = "development"
os.environ["STORAGE_BACKEND"] = "local"
os.environ["UPLOAD_DIR"] = "/tmp/mb16-test-uploads"

from fastapi.testclient import TestClient  # noqa: E402
from app import auth  # noqa: E402
from app.main import app  # noqa: E402


client = TestClient(app)
ADMIN = {"X-Debug-User-Id": "9001"}
USER = {"X-Debug-User-Id": "1001"}
USER2 = {"X-Debug-User-Id": "1002"}
PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Y9ZQmcAAAAASUVORK5CYII="
)
VIDEO = b"mb16-browser-test-video"


def product_payload(article: str = "MB16-CI-001") -> dict[str, str]:
    return {
        "name": "Test Jacket",
        "article": article,
        "price": "120000",
        "colors": "Black, Beige, Black",
        "sizes": "48, 50, 48",
        "category": "Одежда",
        "description": "CI end-to-end test",
    }


def image_files(count: int = 3):
    return [("images", (f"{i}.png", PNG, "image/png")) for i in range(count)]


def product_files(with_video: bool = False):
    files = image_files()
    if with_video:
        files.append(("video", ("clip.mp4", VIDEO, "video/mp4")))
    return files


def admin_request(request_id: int) -> dict:
    requests = client.get("/api/admin/fittings", headers=ADMIN).json()
    return next(r for r in requests if r["id"] == request_id)


def signed_init_data(token: str, user_id: int, auth_date: int | None = None) -> str:
    values = {
        "auth_date": str(auth_date if auth_date is not None else int(time.time())),
        "query_id": "AAE2E_MB16",
        "user": json.dumps(
            {"id": user_id, "first_name": "Telegram", "last_name": "User", "username": "mb16_e2e"},
            separators=(",", ":"),
            ensure_ascii=False,
        ),
    }
    data_check_string = "\n".join(f"{key}={values[key]}" for key in sorted(values))
    secret_key = hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()
    values["hash"] = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    return urlencode(values)


def test_full_mvp_flow_and_guardrails():
    root = client.get("/")
    assert root.status_code == 200
    assert "bottomNav" in root.text
    assert client.get("/health").json() == {"ok": True}
    assert client.get("/api/me", headers=ADMIN).json()["is_admin"] is True
    assert client.get("/api/admin/products", headers=USER).status_code == 403

    data = product_payload()
    assert client.post("/api/admin/products", headers=ADMIN, data=data, files=image_files(2)).status_code == 400

    response = client.post("/api/admin/products", headers=ADMIN, data=data, files=product_files(with_video=True))
    assert response.status_code == 200, response.text
    product = response.json()
    product_id = product["id"]
    assert product["colors"] == ["Black", "Beige"]
    assert product["sizes"] == ["48", "50"]
    assert len(product["media"]) == 4
    assert [m["type"] for m in product["media"]] == ["image", "image", "image", "video"]

    response = client.post("/api/admin/products", headers=ADMIN, data=data, files=image_files())
    assert response.status_code == 409, response.text

    response = client.patch(
        f"/api/admin/products/{product_id}",
        headers=ADMIN,
        json={
            "name": "Updated Jacket",
            "article": "MB16-CI-002",
            "price": 125000,
            "category": "Одежда",
            "colors": ["Black", "Beige", "Black"],
            "sizes": ["48", "50", "48"],
            "description": "Updated CI end-to-end test",
        },
    )
    assert response.status_code == 200, response.text
    assert response.json()["article"] == "MB16-CI-002"
    assert response.json()["price"] == 125000
    assert response.json()["colors"] == ["Black", "Beige"]
    assert response.json()["sizes"] == ["48", "50"]

    products = client.get("/api/products", headers=USER).json()
    assert len(products) == 1

    response = client.post(
        "/api/selection",
        headers=USER,
        json={"product_id": product_id, "color": "Black", "size": "999"},
    )
    assert response.status_code == 400, response.text

    selection_body = {"product_id": product_id, "color": "Black", "size": "48"}
    first_add = client.post("/api/selection", headers=USER, json=selection_body)
    second_add = client.post("/api/selection", headers=USER, json=selection_body)
    assert first_add.status_code == 200
    assert second_add.status_code == 200
    assert first_add.json()["id"] == second_add.json()["id"]
    assert len(client.get("/api/selection", headers=USER).json()) == 1

    assert client.post("/api/selection", headers=USER2, json=selection_body).status_code == 200

    yesterday = (date.today() - timedelta(days=1)).isoformat()
    response = client.post(
        "/api/fittings",
        headers=USER,
        json={"date": yesterday, "time": "14:00:00", "comment": "past"},
    )
    assert response.status_code == 400, response.text

    fitting_date = (date.today() + timedelta(days=1)).isoformat()
    response = client.post(
        "/api/fittings",
        headers=USER,
        json={"date": fitting_date, "time": "14:00:00", "comment": "primary"},
    )
    assert response.status_code == 200, response.text
    request_id = response.json()["id"]
    item_id = admin_request(request_id)["items"][0]["id"]

    response = client.patch(
        f"/api/admin/fittings/{request_id}",
        headers=ADMIN,
        json={"status": "confirmed", "confirmed_date": fitting_date, "confirmed_time": "14:30:00"},
    )
    assert response.status_code == 400, response.text

    assert client.patch(
        f"/api/admin/fittings/{request_id}/items/{item_id}",
        headers=ADMIN,
        json={"availability": "available"},
    ).status_code == 200

    response = client.patch(
        f"/api/admin/fittings/{request_id}",
        headers=ADMIN,
        json={
            "status": "confirmed",
            "confirmed_date": fitting_date,
            "confirmed_time": "14:30:00",
            "admin_note": "Подтверждено",
        },
    )
    assert response.status_code == 200, response.text

    assert client.patch(
        f"/api/admin/fittings/{request_id}/items/{item_id}",
        headers=ADMIN,
        json={"availability": "unavailable"},
    ).status_code == 409

    assert client.patch(
        f"/api/admin/products/{product_id}/status",
        headers=ADMIN,
        json={"status": "sold"},
    ).status_code == 409

    assert client.patch(
        f"/api/admin/fittings/{request_id}",
        headers=ADMIN,
        json={"status": "declined"},
    ).status_code == 409

    rescheduled_date = (date.today() + timedelta(days=2)).isoformat()
    response = client.patch(
        f"/api/admin/fittings/{request_id}",
        headers=ADMIN,
        json={
            "confirmed_date": rescheduled_date,
            "confirmed_time": "15:15:00",
            "admin_note": "Перенос по согласованию",
        },
    )
    assert response.status_code == 200, response.text
    updated_request = admin_request(request_id)
    assert updated_request["confirmed_date"] == rescheduled_date
    assert updated_request["confirmed_time"] == "15:15"
    assert updated_request["admin_note"] == "Перенос по согласованию"

    second_date = (date.today() + timedelta(days=3)).isoformat()
    response = client.post(
        "/api/fittings",
        headers=USER2,
        json={"date": second_date, "time": "16:00:00", "comment": "competing fitting"},
    )
    assert response.status_code == 200, response.text
    request2_id = response.json()["id"]
    item2_id = admin_request(request2_id)["items"][0]["id"]
    assert client.patch(
        f"/api/admin/fittings/{request2_id}/items/{item2_id}",
        headers=ADMIN,
        json={"availability": "available"},
    ).status_code == 200
    response = client.patch(
        f"/api/admin/fittings/{request2_id}",
        headers=ADMIN,
        json={"status": "confirmed", "confirmed_date": second_date, "confirmed_time": "16:30:00"},
    )
    assert response.status_code == 409, response.text

    response = client.post(
        f"/api/fittings/{request_id}/purchases",
        headers=USER,
        json={"item_ids": [item_id]},
    )
    assert response.status_code == 400, response.text

    response = client.patch(
        f"/api/admin/fittings/{request_id}",
        headers=ADMIN,
        json={"status": "completed"},
    )
    assert response.status_code == 200, response.text

    assert client.patch(
        f"/api/admin/fittings/{request_id}",
        headers=ADMIN,
        json={"status": "cancelled"},
    ).status_code == 409

    response = client.post(
        f"/api/fittings/{request_id}/purchases",
        headers=USER,
        json={"item_ids": [item_id]},
    )
    assert response.status_code == 200, response.text
    purchases = client.get("/api/purchases/my", headers=USER).json()
    assert len(purchases) == 1
    assert purchases[0]["confirmed"] is False

    response = client.post(
        f"/api/admin/fittings/{request_id}/items/{item_id}/confirm-sale",
        headers=ADMIN,
    )
    assert response.status_code == 200, response.text
    assert client.post(
        f"/api/admin/fittings/{request_id}/items/{item_id}/confirm-sale",
        headers=ADMIN,
    ).status_code == 200

    response = client.post(
        f"/api/fittings/{request_id}/purchases",
        headers=USER,
        json={"item_ids": []},
    )
    assert response.status_code == 409, response.text

    assert client.patch(
        f"/api/admin/products/{product_id}/status",
        headers=ADMIN,
        json={"status": "available"},
    ).status_code == 409

    assert client.patch(
        f"/api/admin/fittings/{request2_id}/items/{item2_id}",
        headers=ADMIN,
        json={"availability": "available"},
    ).status_code == 409
    response = client.patch(
        f"/api/admin/fittings/{request2_id}",
        headers=ADMIN,
        json={"status": "confirmed", "confirmed_date": second_date, "confirmed_time": "16:30:00"},
    )
    assert response.status_code == 409, response.text

    assert client.get("/api/products", headers=USER).json() == []
    assert client.get("/api/selection", headers=USER).json() == []
    assert client.get("/api/selection", headers=USER2).json() == []
    purchases = client.get("/api/purchases/my", headers=USER).json()
    assert purchases[0]["confirmed"] is True

    assert client.patch(
        f"/api/admin/fittings/{request2_id}",
        headers=ADMIN,
        json={"status": "cancelled"},
    ).status_code == 200


def test_telegram_auth_signature_and_timestamp_guardrails(monkeypatch):
    token = "test-token"
    monkeypatch.setattr(auth.settings, "telegram_bot_token", token)

    valid = signed_init_data(token, user_id=777001)
    values = auth._validate_init_data(valid)
    assert json.loads(values["user"])["id"] == 777001
    identity = auth.resolve_identity(valid, None)
    assert identity.telegram_id == 777001
    assert identity.username == "mb16_e2e"

    with pytest.raises(HTTPException) as malformed:
        auth._validate_init_data("auth_date=not-a-number&hash=irrelevant")
    assert malformed.value.status_code == 401

    future = int(time.time()) + 3600
    with pytest.raises(HTTPException) as future_error:
        auth._validate_init_data(f"auth_date={future}&hash=irrelevant")
    assert future_error.value.status_code == 401

    expired = signed_init_data(
        token,
        user_id=777002,
        auth_date=int(time.time()) - auth.settings.auth_max_age_seconds - 1,
    )
    with pytest.raises(HTTPException) as expired_error:
        auth._validate_init_data(expired)
    assert expired_error.value.status_code == 401

    monkeypatch.setattr(auth.settings, "app_env", "production")
    with pytest.raises(HTTPException) as debug_in_production:
        auth.resolve_identity(None, "9001")
    assert debug_in_production.value.status_code == 401
