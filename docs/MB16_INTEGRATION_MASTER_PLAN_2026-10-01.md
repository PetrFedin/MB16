# MB16 — Clienteling Integration Master Plan

**Status:** PLANNED  
**Date:** 2026-10-01  
**Canonical file:** `docs/MB16_INTEGRATION_MASTER_PLAN_2026-10-01.md`

## Purpose
MB16 remains a focused private-showroom/clienteling product. This plan deepens client profile, fitting, stylist and post-visit workflows without turning MB16 into a second FLASHIN marketplace.

## Authority boundary
MB16 owns products, availability, fittings, client history and showroom administration. External projects may provide UI/components/patterns only.

## Planned integrations

| Capability | Source | Decision |
|---|---|---|
| Client Profile | native | ADOPT |
| Stylist Workspace | Twenty patterns | ADAPT |
| Appointment capacity | FullCalendar | ADOPT |
| External availability patterns | Cal.com | REFERENCE/ADAPT |
| Hold / reservation TTL | native | ADOPT |
| Look Builder | native + SortableJS | ADOPT |
| Media upload | FilePond | ADOPT |
| Product/look gallery | Embla Carousel | ADOPT |
| QR fitting/item lookup | qr-scanner | ADOPT |
| Post-visit lifecycle | native | ADOPT |

## Phase 0 — Keep the MVP narrow
Do not add payment orchestration, broad CRM, AI recommendation or warehouse complexity before the showroom/fitting path is reliable.

## Phase 1 — Client Profile
Add client-confirmed sizes, category/brand preferences, colours, explicit dislikes, wishlist, fitting history, purchases, contact consent and stylist notes.

Stylist notes are access-controlled and must be distinguishable from customer-confirmed facts.

## Phase 2 — Stylist Workspace
Use Twenty interaction patterns, not its database.

Flow:
`today's fittings -> client -> prepared products/look -> notes -> outcome -> follow-up`

Provide upcoming appointments, client context, wishlist, previous purchases/fittings, saved looks and follow-up tasks.

## Phase 3 — Appointment Capacity
Use FullCalendar in admin.

Server model:
- stylist/resource;
- fitting room;
- slot;
- capacity;
- appointment;
- reschedule/cancel/no-show.

Double booking must be prevented server-side. Cal.com is only an availability/integration reference; MB16 owns the confirmed appointment.

## Phase 4 — Hold TTL
Lifecycle:
`available -> held -> sold / released / expired`

Each hold has client, variant, expires_at, appointment/context and release reason. Client timer is not authority.

## Phase 5 — Look Builder
Create ordered looks with product variants, stylist comment, client, status and outcome. SortableJS handles ordering in UI; backend persists canonical order.

## Phase 6 — Media UX
FilePond handles upload validation/progress/retry/reorder. Embla provides touch-first gallery. Original media remains server/object-storage authority.

## Phase 7 — QR showroom flow
Use QR for product lookup, appointment check-in and prepared-look retrieval. QR carries opaque IDs only — no client PII.

## Phase 8 — Post-visit lifecycle
Record attendance/no-show, tried items, liked/disliked, hold/purchase, follow-up date and consented communication.

## Prohibited
- duplicating FLASHIN commerce/payment scope;
- treating stylist notes as confirmed customer facts;
- trusting client-side capacity;
- exposing PII in QR;
- permanent holds;
- AI recommendations before clean history exists.

## Issue order
1. MB16-INT-00 Client Profile
2. MB16-INT-01 Stylist Workspace
3. MB16-INT-02 Appointment Capacity
4. MB16-INT-03 Hold TTL
5. MB16-INT-04 Look Builder
6. MB16-INT-05 Media workflow
7. MB16-INT-06 QR workflow
8. MB16-INT-07 Post-visit lifecycle

**Implementation instruction:** deepen private clienteling; do not broaden MB16 into a generic marketplace.

## Additional wave — calendar handoff, reminders and staff account security

### iCalendar appointment handoff — ADOPT

Reference: https://github.com/kewisch/ical.js

After the Appointment Capacity model is stable, generate standards-based calendar artefacts for confirmed fittings.

Support:

- add-to-calendar .ics;
- rescheduled appointment update;
- cancellation;
- timezone-safe start/end;
- location/contact text;
- opaque MB16 appointment identifier.

The calendar entry is a projection. MB16 remains the confirmed appointment authority.

Imported external calendar events should not automatically create fittings.

### Web Push fitting reminders — ADOPT/CONDITIONAL

Reference: https://github.com/web-push-libs/web-push

Use when the web/PWA channel and browser support make it useful.

Reminder types:

- fitting tomorrow/today;
- fitting changed/cancelled;
- hold expiring before fitting;
- stylist follow-up ready.

Consent/notification preference must be explicit. Push delivery status does not equal appointment attendance.

If Telegram remains the dominant channel, Web Push can stay conditional.

### Passkeys for staff/admin — ADOPT

Reference: https://github.com/duo-labs/py_webauthn

Apply first to:

- administrators;
- stylists with access to private client notes/history;
- staff who can change stock holds or client records.

Use step-up authentication for bulk export, role changes and sensitive client-data operations.

Passkeys attach to the existing account model; no parallel staff directory.

### Acceptance extension

- .ics reflects server-authoritative appointment version;
- cancellation/reschedule cannot leave conflicting calendar versions without sequence/version metadata;
- push honours consent/preferences;
- staff passkey recovery/removal is audited;
- none of these additions introduce payment/marketplace scope.

**Sequencing:** appointment authority first, then ICS/reminders; staff passkeys can be introduced once authentication/session behavior is stable.

## Additional wave — fitting preparation, showroom scan and clienteling conversion

This wave deepens the actual appointment execution after Client Profile / Appointment / Hold / Look authorities exist.

### Fitting Preparation Board — ADOPT

For every upcoming fitting, generate a preparation workspace:

- appointment/client;
- stylist;
- room;
- planned looks/items;
- hold state;
- required sizes/alternatives;
- product availability;
- preparation owner/status;
- missing-item reason;
- client notes relevant to the visit.

Flow:

appointment confirmed -> proposed/prepared items -> physical pick -> ready check -> fitting -> outcome

Preparation status must never overwrite stock/hold authority; it references those records.

### Showroom Item Scan — ADOPT

Browser scanner reference: https://github.com/zxing-js/browser

Support QR/EAN/barcode scan for staff where product labels carry a compatible code.

Use cases:

- find product/variant;
- add/remove item from fitting preparation;
- verify prepared item;
- record tried item;
- retrieve hold status.

Scanner output is only an identifier candidate. Server resolves it to MB16's canonical product/variant and validates staff permissions.

Do not expose client data in physical product QR/barcodes.

### Shareable Digital Lookbook — ADOPT

Allow stylist to create a time-limited client share link for selected looks/items.

Link properties:

- opaque high-entropy token;
- client/look scope;
- expiry;
- revoke;
- optional view analytics;
- no private stylist notes;
- no general client profile exposure.

The lookbook is a read projection; product availability/price are loaded from current MB16 state where appropriate.

### Clienteling Follow-up Cadence — ADOPT

Create explicit follow-up tasks after fitting:

- send selected look;
- hold-expiry reminder;
- request feedback;
- new arrival matching explicit preference;
- personal appointment invitation.

Respect contact consent/channel preference and frequency limits.

This remains one-to-one clienteling, not broad marketing automation.

### Fitting Conversion Funnel — ADOPT

Measure operational conversion using authoritative facts:

appointment booked -> attended -> items prepared -> items tried -> liked/saved -> held -> purchased

Metrics may include:

- attendance/no-show;
- preparation completeness;
- try-to-like;
- like-to-hold;
- hold-to-purchase;
- stylist/client cohort.

Do not infer salesperson quality from tiny samples; always expose denominator and period.

### Additional acceptance

- fitting board reconciles to actual holds/availability;
- scan cannot mutate an unknown/wrong variant;
- share token expires/revokes and leaks no private notes;
- follow-up obeys consent/frequency rules;
- funnel is reproducible from event/order/fitting facts.

**Sequencing:** Client Profile + Appointment + Hold -> preparation board -> scan -> lookbook/follow-up -> conversion analytics.

## Additional wave — offline showroom operations and stocktake reconciliation

This wave makes MB16 usable during a fitting even when connectivity is unreliable.

### Dexie offline staff store — ADOPT

Reference: https://github.com/dexie/Dexie.js

Use IndexedDB via Dexie for a bounded staff-only offline cache containing:

- today's appointments;
- prepared looks/items;
- canonical product/variant identifiers;
- last-known availability/hold projection;
- scan queue;
- fitting outcome drafts.

Do **not** cache full private client history or unnecessary personal data.

Each local record carries:

- server version/updated_at;
- fetched_at;
- sync state;
- local mutation ID.

### Offline mutation queue — ADOPT

Allowed offline actions should be intentionally narrow, for example:

- mark item physically prepared;
- scan/add item to fitting draft;
- record tried/liked/disliked draft;
- collect fitting notes draft.

High-risk/authority actions stay online-only:

- final stock hold allocation;
- stock correction;
- role/member changes;
- sensitive client export;
- destructive deletion.

On reconnect:

local mutation -> idempotent API command -> conflict/version check -> accepted/rejected -> local reconciliation

Never use last-known offline availability to promise/reserve stock without server confirmation.

### Showroom Cycle Count / Stocktake — ADOPT

Create a lightweight inventory verification workflow:

stocktake session -> location/rack -> scanned variants -> expected projection -> discrepancy -> review -> approved inventory correction in source system/authority

Store:

- session;
- operator;
- scan event;
- variant;
- observed quantity;
- expected quantity;
- discrepancy reason;
- reconciliation status.

MB16 should not become a warehouse ERP. If inventory truth comes from another system, approved corrections must flow to/through that authority.

### Conflict UI — ADOPT

Explicitly surface reconnect conflicts:

- item sold while offline;
- hold expired;
- appointment changed;
- product/variant deactivated;
- duplicate scan/mutation.

Staff chooses or follows deterministic domain resolution; do not silently overwrite newer server state.

### Additional acceptance

- app can open today's fitting workspace offline after prior sync;
- offline queue is idempotent across refresh/retry;
- server authority always wins stock/hold conflicts;
- cached PII is minimized and clearable on logout/device deauthorization;
- stocktake discrepancies require explicit reconciliation before stock changes.

**Sequencing:** appointment/preparation/scan flows first -> Dexie cache -> offline queue -> conflict handling -> stocktake.

