# MB16 end-to-end QA

This file defines what must be green before the MVP is treated as ready for a real Telegram/Timeweb launch.

## Automated checks

GitHub Actions (`.github/workflows/ci.yml`) is configured to run on pushes and pull requests.

It checks:

1. Python bytecode compilation for `app/` and `scripts/`.
2. Development preflight configuration.
3. JavaScript syntax with Node 22.
4. The full API flow on SQLite.
5. The same full API flow on PostgreSQL 16.
6. A real Chromium browser flow through the client and admin UI.
7. Docker image build.

A branch is not considered verified merely because the files exist. Treat the automated layer as verified only when the GitHub Actions run for the branch/PR is green.

## Automated API E2E scenario

`tests/test_flow.py` covers the following path and guardrails:

- application HTML and `/health` are reachable;
- admin access is denied to a normal client;
- a product requires 3–5 images;
- duplicate article creation is rejected;
- product editing works;
- duplicate colors/sizes are normalized;
- invalid color/size selection is rejected;
- duplicate selection addition is idempotent;
- a fitting cannot be requested in the past;
- a fitting cannot be confirmed before every item is checked;
- item availability cannot be changed after fitting confirmation;
- a product reserved in a confirmed fitting cannot be manually marked sold;
- invalid fitting status transitions are rejected;
- a confirmed fitting can be rescheduled to a future time;
- the same product cannot be confirmed in two fittings at once;
- a client cannot mark purchases before the visit is completed;
- a completed fitting cannot be rolled back to cancelled;
- sale confirmation is idempotent;
- a confirmed sale cannot be removed by the client from purchase history;
- a confirmed sale cannot be returned to the catalog;
- sold products disappear from active selections;
- purchase history preserves the confirmed sale;
- malformed or far-future Telegram `auth_date` values are rejected.

## Automated browser E2E scenario

`tests/test_browser_e2e.py` launches Chromium with a mobile viewport and exercises the UI, not just API calls:

1. Admin opens the admin section and creates a product with three photos.
2. Client opens the product, selects color/size and adds it to the selection.
3. Client submits a fitting request.
4. Admin checks availability and confirms the fitting.
5. Admin reschedules the confirmed fitting through **Save time**.
6. Admin marks **Client arrived**.
7. Client marks the item as purchased.
8. Admin confirms the sale.
9. Client sees the product removed from catalog/selection and preserved as a confirmed purchase.

The browser test stubs only the external Telegram SDK script. All MB16 HTML, JavaScript, API calls, database writes and local media handling use the running application.

## Optional local acceptance check

Run locally:

```bash
make start-bg
make health
```

Open:

- client: `http://localhost:8000/?debug_user=1001`
- admin: `http://localhost:8000/?debug_user=9001`

This manual pass is useful for visual judgment on a real phone-sized window, but it is no longer the only UI validation layer because the core client/admin flow also runs automatically in Chromium CI.

## Production-only checks

These cannot be fully verified without the real external services and must be checked after Timeweb/Telegram configuration:

### Telegram

- real `Telegram.WebApp.initData` authentication succeeds;
- invalid/expired initData is rejected;
- admin Telegram IDs receive a new fitting notification;
- the client receives fitting confirmation/reschedule notification;
- the Mini App menu button opens the deployed HTTPS URL.

### Timeweb PostgreSQL

- production `DATABASE_URL` connects over the intended private/public network;
- `/health` returns `{"ok": true}` after restart;
- data survives application container restarts.

### S3/Object Storage

- 3–5 images upload and render from the public S3 URL;
- optional video uploads and plays;
- oversize/unsupported files are rejected;
- uploaded media remains available after application redeploy.

## Current MVP boundary

This QA scope intentionally does not validate online payment, quantitative SKU inventory, CRM, personal managers, AI styling, recommendations, conversion analytics, delivery, loyalty or promotions because those modules are not part of the current MB16 MVP.
