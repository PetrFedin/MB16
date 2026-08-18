import base64
import os
from datetime import date, timedelta
from pathlib import Path

import pytest
from playwright.sync_api import expect, sync_playwright

BASE_URL = os.environ.get("BROWSER_E2E_BASE_URL", "").rstrip("/")
pytestmark = pytest.mark.skipif(not BASE_URL, reason="Browser E2E requires BROWSER_E2E_BASE_URL")

PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Y9ZQmcAAAAASUVORK5CYII="
)


def prepare_images(tmp_path: Path) -> list[str]:
    paths = []
    for index in range(3):
        path = tmp_path / f"browser-{index}.png"
        path.write_bytes(PNG)
        paths.append(str(path))
    return paths


def open_debug_page(browser, user_id: int):
    page = browser.new_page(viewport={"width": 390, "height": 844})
    page.route(
        "https://telegram.org/js/telegram-web-app.js",
        lambda route: route.fulfill(status=200, content_type="application/javascript", body=""),
    )
    page.goto(f"{BASE_URL}/?debug_user={user_id}", wait_until="domcontentloaded")
    expect(page.locator("#bottomNav")).to_be_visible()
    return page


def test_browser_client_admin_purchase_flow(tmp_path):
    fitting_date = (date.today() + timedelta(days=2)).isoformat()
    images = prepare_images(tmp_path)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        admin = open_debug_page(browser, 9001)
        client = open_debug_page(browser, 1001)

        admin.locator('#bottomNav [data-v="admin"]').click()
        expect(admin.locator("#newP")).to_be_visible()
        admin.locator("#newP").click()
        admin.locator("#pn").fill("Browser Jacket")
        admin.locator("#pa").fill("MB16-PW-001")
        admin.locator("#pp").fill("135000")
        admin.locator("#pc2").fill("Black, Beige")
        admin.locator("#ps2").fill("48, 50")
        admin.locator("#pd").fill("Browser end-to-end product")
        admin.locator("#pi").set_input_files(images)
        admin.locator("#publish").click()
        expect(admin.get_by_text("MB16-PW-001", exact=False)).to_be_visible()

        client.reload(wait_until="domcontentloaded")
        expect(client.locator(".product-card")).to_have_count(1)
        client.locator(".product-card").click()
        expect(client.locator("#add")).to_be_visible()
        client.locator("#pc").select_option(label="Black")
        client.locator("#ps").select_option(label="48")
        client.locator("#add").click()

        client.locator('#bottomNav [data-v="selection"]').click()
        expect(client.locator("#book")).to_be_visible()
        client.locator("#book").click()
        client.locator("#fd").fill(fitting_date)
        client.locator("#ft").fill("14:00")
        client.locator("#fc").fill("Browser E2E fitting")
        client.locator("#sendFit").click()
        expect(client.get_by_text("Примерка #", exact=False)).to_be_visible()

        admin.reload(wait_until="domcontentloaded")
        admin.locator('#bottomNav [data-v="admin"]').click()
        expect(admin.locator('[data-tab="requests"]')).to_be_visible()
        admin.locator('[data-tab="requests"]').click()
        request = admin.locator("[data-r]").first
        expect(request).to_be_visible()
        request.locator('[data-av$=":available"]').click()

        request = admin.locator("[data-r]").first
        request.locator('[data-up$=":confirmed"]').click()
        request = admin.locator("[data-r]").first
        expect(request.get_by_text("Подтверждена", exact=True)).to_be_visible()

        request.locator("[data-time]").fill("15:00")
        request.locator("[data-note]").fill("Перенос через browser E2E")
        request.locator("[data-reschedule]").click()
        request = admin.locator("[data-r]").first
        expect(request.locator("[data-time]")).to_have_value("15:00")

        request.locator('[data-up$=":completed"]').click()
        request = admin.locator("[data-r]").first
        expect(request.get_by_text("Клиент пришёл", exact=True)).to_be_visible()

        client.locator('#bottomNav [data-v="fittings"]').click()
        buy_button = client.locator("[data-buy]")
        expect(buy_button).to_be_visible()
        buy_button.click()
        purchase_checkbox = client.locator("[data-ci]")
        expect(purchase_checkbox).to_be_visible()
        purchase_checkbox.check()
        client.locator("#saveBuy").click()
        expect(client.get_by_text("ожидает подтверждения", exact=False)).to_be_visible()

        admin.reload(wait_until="domcontentloaded")
        admin.locator('#bottomNav [data-v="admin"]').click()
        admin.locator('[data-tab="requests"]').click()
        request = admin.locator("[data-r]").first
        sale_button = request.locator("[data-sale]")
        expect(sale_button).to_be_visible()
        sale_button.click()
        request = admin.locator("[data-r]").first
        expect(request.get_by_text("Продажа подтверждена", exact=True)).to_be_visible()

        client.locator('#bottomNav [data-v="catalog"]').click()
        expect(client.locator(".product-card")).to_have_count(0)
        client.locator('#bottomNav [data-v="selection"]').click()
        expect(client.get_by_text("Подборка пустая", exact=True)).to_be_visible()
        client.locator('#bottomNav [data-v="purchases"]').click()
        expect(client.get_by_text("подтверждено", exact=False)).to_be_visible()
        expect(client.get_by_text("Browser Jacket", exact=True)).to_be_visible()

        browser.close()
