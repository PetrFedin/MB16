import base64
import os
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

TEST_DB = Path("/tmp/mb16-test.db")
if TEST_DB.exists():
    TEST_DB.unlink()
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB}"
os.environ["APP_ENV"] = "development"
os.environ["STORAGE_BACKEND"] = "local"
os.environ["UPLOAD_DIR"] = "/tmp/mb16-test-uploads"

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402


client = TestClient(app)
ADMIN = {"X-Debug-User-Id": "9001"}
USER = {"X-Debug-User-Id": "1001"}
PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Y9ZQmcAAAAASUVORK5CYII="
)


def test_full_mvp_flow():
    assert client.get("/health").json() == {"ok": True}
    assert client.get("/api/me", headers=ADMIN).json()["is_admin"] is True
    assert client.get("/api/admin/products", headers=USER).status_code == 403

    data = {
        "name": "Test Jacket",
        "article": "MB16-CI-001",
        "price": "120000",
        "colors": "Black, Beige",
        "sizes": "48, 50",
        "category": "Одежда",
        "description": "CI smoke test",
    }
    too_few_files = [("images", (f"bad-{i}.png", PNG, "image/png")) for i in range(2)]
    assert client.post("/api/admin/products", headers=ADMIN, data=data, files=too_few_files).status_code == 400

    files = [("images", (f"{i}.png", PNG, "image/png")) for i in range(3)]
    response = client.post("/api/admin/products", headers=ADMIN, data=data, files=files)
    assert response.status_code == 200, response.text
    product_id = response.json()["id"]

    response = client.patch(
        f"/api/admin/products/{product_id}",
        headers=ADMIN,
        json={
            "name": "Updated Jacket",
            "article": "MB16-CI-002",
            "price": 125000,
            "category": "Одежда",
            "colors": ["Black", "Beige"],
            "sizes": ["48", "50"],
            "description": "Updated CI smoke test",
        },
    )
    assert response.status_code == 200, response.text
    assert response.json()["article"] == "MB16-CI-002"
    assert response.json()["price"] == 125000

    products = client.get("/api/products", headers=USER).json()
    assert len(products) == 1

    response = client.post(
        "/api/selection",
        headers=USER,
        json={"product_id": product_id, "color": "Black", "size": "999"},
    )
    assert response.status_code == 400, response.text

    response = client.post(
        "/api/selection",
        headers=USER,
        json={"product_id": product_id, "color": "Black", "size": "48"},
    )
    assert response.status_code == 200, response.text

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
        json={"date": fitting_date, "time": "14:00:00", "comment": "test"},
    )
    assert response.status_code == 200, response.text
    request_id = response.json()["id"]

    admin_request = client.get("/api/admin/fittings", headers=ADMIN).json()[0]
    item_id = admin_request["items"][0]["id"]

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

    response = client.post(
        f"/api/fittings/{request_id}/purchases",
        headers=USER,
        json={"item_ids": [item_id]},
    )
    assert response.status_code == 200, response.text
    assert len(client.get("/api/purchases/my", headers=USER).json()) == 1

    response = client.post(
        f"/api/admin/fittings/{request_id}/items/{item_id}/confirm-sale",
        headers=ADMIN,
    )
    assert response.status_code == 200, response.text
    assert client.get("/api/products", headers=USER).json() == []
    assert client.get("/api/purchases/my", headers=USER).json()[0]["confirmed"] is True
