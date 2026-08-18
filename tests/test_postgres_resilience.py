import base64
import os
import shutil
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from pathlib import Path

import pytest

if os.environ.get("RESILIENCE_E2E") != "1":
    pytest.skip("Resilience E2E runs in its dedicated CI step", allow_module_level=True)

DATABASE_URL = os.environ.get("TEST_DATABASE_URL", "").strip()
if not DATABASE_URL.startswith("postgresql"):
    pytest.skip("Resilience E2E requires PostgreSQL", allow_module_level=True)

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
UPLOAD_DIR = Path("/tmp/mb16-resilience-uploads")
shutil.rmtree(UPLOAD_DIR, ignore_errors=True)
os.environ["DATABASE_URL"] = DATABASE_URL
os.environ["APP_ENV"] = "development"
os.environ["STORAGE_BACKEND"] = "local"
os.environ["UPLOAD_DIR"] = str(UPLOAD_DIR)

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402

ADMIN = {"X-Debug-User-Id": "9001"}
USER_A = {"X-Debug-User-Id": "2101"}
USER_B = {"X-Debug-User-Id": "2102"}
USER_C = {"X-Debug-User-Id": "2201"}
USER_D = {"X-Debug-User-Id": "2202"}
PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Y9ZQmcAAAAASUVORK5CYII="
)


def images():
    return [("images", (f"race-{i}.png", PNG, "image/png")) for i in range(3)]


def create_product(client: TestClient, article: str) -> int:
    response = client.post(
        "/api/admin/products",
        headers=ADMIN,
        data={
            "name": "Concurrency Jacket",
            "article": article,
            "price": "99000",
            "colors": "Black",
            "sizes": "48",
            "category": "Одежда",
            "description": "PostgreSQL resilience test",
        },
        files=images(),
    )
    assert response.status_code == 200, response.text
    return response.json()["id"]


def create_fitting(client: TestClient, headers: dict[str, str], product_id: int, day_offset: int) -> tuple[int, int, str]:
    assert client.post(
        "/api/selection",
        headers=headers,
        json={"product_id": product_id, "color": "Black", "size": "48"},
    ).status_code == 200
    fitting_date = (date.today() + timedelta(days=day_offset)).isoformat()
    response = client.post(
        "/api/fittings",
        headers=headers,
        json={"date": fitting_date, "time": "14:00:00", "comment": "resilience"},
    )
    assert response.status_code == 200, response.text
    request_id = response.json()["id"]
    requests = client.get("/api/admin/fittings", headers=ADMIN).json()
    request = next(r for r in requests if r["id"] == request_id)
    item_id = request["items"][0]["id"]
    assert client.patch(
        f"/api/admin/fittings/{request_id}/items/{item_id}",
        headers=ADMIN,
        json={"availability": "available"},
    ).status_code == 200
    return request_id, item_id, fitting_date


def get_admin_request(client: TestClient, request_id: int) -> dict:
    requests = client.get("/api/admin/fittings", headers=ADMIN).json()
    return next(r for r in requests if r["id"] == request_id)


def confirm_fitting(client: TestClient, request_id: int, fitting_date: str) -> int:
    return client.patch(
        f"/api/admin/fittings/{request_id}",
        headers=ADMIN,
        json={
            "status": "confirmed",
            "confirmed_date": fitting_date,
            "confirmed_time": "15:00:00",
        },
    ).status_code


def test_concurrent_first_requests_create_one_user_without_500():
    headers = {"X-Debug-User-Id": "2199"}
    barrier = threading.Barrier(2)

    def load_me() -> tuple[int, int | None]:
        with TestClient(app) as local_client:
            barrier.wait(timeout=10)
            response = local_client.get("/api/me", headers=headers)
            telegram_id = response.json().get("telegram_id") if response.status_code == 200 else None
            return response.status_code, telegram_id

    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(load_me)
        second = pool.submit(load_me)
        results = [first.result(timeout=20), second.result(timeout=20)]

    assert [status for status, _ in results] == [200, 200]
    assert [telegram_id for _, telegram_id in results] == [2199, 2199]


def test_concurrent_confirmations_reserve_product_once():
    with TestClient(app) as setup_client:
        product_id = create_product(setup_client, "MB16-RACE-001")
        request_a, _, date_a = create_fitting(setup_client, USER_A, product_id, 5)
        request_b, _, date_b = create_fitting(setup_client, USER_B, product_id, 6)

    barrier = threading.Barrier(2)

    def confirm(request_id: int, fitting_date: str) -> int:
        with TestClient(app) as local_client:
            barrier.wait(timeout=10)
            return confirm_fitting(local_client, request_id, fitting_date)

    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(confirm, request_a, date_a)
        second = pool.submit(confirm, request_b, date_b)
        statuses = sorted([first.result(timeout=20), second.result(timeout=20)])

    assert statuses == [200, 409]
    with TestClient(app) as verify_client:
        requests = verify_client.get("/api/admin/fittings", headers=ADMIN).json()
        relevant = [r for r in requests if r["id"] in {request_a, request_b}]
        assert sum(r["status"] == "confirmed" for r in relevant) == 1
        assert sum(r["status"] == "new" for r in relevant) == 1


def test_completed_fitting_holds_until_purchase_decision_then_releases():
    with TestClient(app) as client:
        product_id = create_product(client, "MB16-HOLD-001")
        request_a, item_a, date_a = create_fitting(client, USER_C, product_id, 7)
        assert confirm_fitting(client, request_a, date_a) == 200

        request_b, _, date_b = create_fitting(client, USER_D, product_id, 8)
        assert confirm_fitting(client, request_b, date_b) == 409

        assert client.patch(
            f"/api/admin/fittings/{request_a}",
            headers=ADMIN,
            json={"status": "completed"},
        ).status_code == 200
        completed = get_admin_request(client, request_a)
        assert completed["purchase_reported"] is False

        assert confirm_fitting(client, request_b, date_b) == 409
        assert client.patch(
            f"/api/admin/products/{product_id}/status",
            headers=ADMIN,
            json={"status": "sold"},
        ).status_code == 409

        response = client.post(
            f"/api/fittings/{request_a}/purchases",
            headers=USER_C,
            json={"item_ids": []},
        )
        assert response.status_code == 200, response.text
        completed = get_admin_request(client, request_a)
        assert completed["purchase_reported"] is True
        assert completed["items"][0]["id"] == item_a
        assert completed["items"][0]["purchased_claimed"] is False

        assert confirm_fitting(client, request_b, date_b) == 200


def test_partial_media_failure_leaves_no_orphans():
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    before = {p.relative_to(UPLOAD_DIR) for p in UPLOAD_DIR.rglob("*") if p.is_file()}
    files = [
        ("images", ("one.png", PNG, "image/png")),
        ("images", ("two.png", PNG, "image/png")),
        ("images", ("bad.txt", b"not-an-image", "text/plain")),
    ]
    with TestClient(app) as client:
        response = client.post(
            "/api/admin/products",
            headers=ADMIN,
            data={
                "name": "Broken media card",
                "article": "MB16-MEDIA-ROLLBACK-001",
                "price": "10000",
                "colors": "Black",
                "sizes": "48",
                "category": "Одежда",
                "description": "must roll back",
            },
            files=files,
        )
        assert response.status_code == 400, response.text
        assert not any(p["article"] == "MB16-MEDIA-ROLLBACK-001" for p in client.get("/api/admin/products", headers=ADMIN).json())

    after = {p.relative_to(UPLOAD_DIR) for p in UPLOAD_DIR.rglob("*") if p.is_file()}
    assert after == before
