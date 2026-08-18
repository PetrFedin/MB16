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
6. Docker image build.

A branch is not considered verified merely because the files exist. Treat the automated layer as verified only when the GitHub Actions run for the branch/PR is green.

## Automated E2E scenario

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

## Manual browser check before production

Run locally:

```bash
make start-bg
make health
```

Open:

- client: `http://localhost:8000/?debug_user=1001`
- admin: `http://localhost:8000/?debug_user=9001`

Verify once in the browser:

1. Admin creates a card with 3–5 photos and optional video.
2. Client opens the card, changes color/size, and adds it to the selection.
3. Client sends a fitting request.
4. Admin marks item availability and confirms the date/time.
5. Admin changes the confirmed time using **Save time** and sees the new value after reload.
6. Admin marks **Client arrived**.
7. Client marks purchased items.
8. Admin confirms the sale.
9. The sold product disappears from the catalog/selection and remains in client purchase history.

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
