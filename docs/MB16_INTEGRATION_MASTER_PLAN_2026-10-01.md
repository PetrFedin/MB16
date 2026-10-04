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

## Additional wave — appointment waitlist and slot backfill

This wave improves fitting-room/stylist utilization without becoming broad campaign automation.

### Appointment Waitlist Authority — ADOPT

Create a waitlist record for clients who explicitly want an earlier/new slot.

Store:

- client;
- preferred date/time windows;
- preferred stylist where relevant;
- duration/service type;
- location/room requirement;
- expiration;
- contact channel/consent;
- priority rule;
- status.

The waitlist is not a confirmed appointment.

### Slot Backfill Engine — ADOPT

Trigger when:

- appointment cancelled;
- slot released;
- stylist/room capacity added;
- hold on a slot expires.

Flow:

available slot -> eligible waitlist candidates -> ordered candidate list -> offer -> offer expiry -> accept -> server confirms appointment

Only one candidate may claim the slot successfully.

### Fairness / Priority Rules — ADOPT

Priority can be based on explicit versioned rules such as:

- request time;
- client-selected urgency;
- stylist requirement;
- service duration fit;
- manual VIP/priority policy where business-approved.

Do not use hidden personal scoring.

Every override stores reason/operator.

### Offer Expiry / Race Safety — ADOPT

A slot offer is a temporary right to accept, not an appointment.

Store:

- offer ID;
- candidate;
- slot version;
- expires_at;
- accepted/rejected/expired;
- resulting appointment ID.

Server-side optimistic locking/transaction prevents two accepted offers creating the same appointment.

### Waitlist-to-Follow-up integration — ADOPT

If a client does not accept:

- try next eligible candidate;
- optionally keep the original client on the waitlist;
- obey notification preferences/frequency.

### Additional acceptance

- a waitlist entry never appears as booked capacity;
- concurrent acceptance cannot double-book;
- priority rule/version is auditable;
- expired offer cannot create appointment;
- cancellation/backfill analytics distinguish offered vs accepted;
- contact consent is respected.

**Sequencing:** Appointment Capacity first -> waitlist -> slot-offer lifecycle -> automated backfill -> utilization analytics.

## Premium innovation wave — private stylist copilot and taste memory

This wave turns MB16 into a premium clienteling tool: AI assists the stylist while the stylist remains the decision-maker and relationship owner.

### Client Taste Memory — ADOPT

Build an explainable preference layer from approved facts:

- explicit likes/dislikes;
- saved looks;
- items tried;
- fitting feedback;
- purchased items;
- preferred brands/categories/colours;
- size/fit preferences;
- stylist-confirmed notes.

Keep distinct:

- user-confirmed preference;
- observed behaviour;
- stylist note;
- model-derived similarity.

### Visual Taste Embeddings — ADAPT

References:

- https://github.com/mlfoundations/open_clip
- https://github.com/qdrant/qdrant

Use a rebuildable visual index to suggest:

- related pieces;
- alternatives to liked items;
- complementary products;
- items near explicit taste examples.

Vector metadata is not product/client-profile authority.

### Stylist Copilot — ADOPT/ADAPT

Typed-agent pattern candidate:

https://github.com/pydantic/pydantic-ai

Inputs:

- Client Profile;
- explicit taste memory;
- appointment context;
- current availability;
- saved/previous looks;
- purchase/fitting history;
- stylist-selected objective.

Structured output:

- proposed looks;
- candidate items/variants;
- reason for each choice;
- availability/hold state;
- known fit context;
- confidence/unknowns;
- alternatives.

The stylist reviews/edits before anything is shown or reserved.

### Why this look — ADOPT

Source-linked explanation examples:

- matches saved silhouette;
- uses preferred colour;
- complements previous purchase;
- alternative to unavailable item;
- fits current fitting objective.

No personality/body judgments.

### Client Presentation Mode — ADOPT

Approved stylist selections become a premium client-facing view:

- 1–3 looks;
- item gallery;
- stylist notes;
- available sizes;
- reserve/hold request;
- appointment context;
- expiring share link.

### Learning Loop — ADOPT

proposed -> shown -> tried -> liked/disliked -> held -> purchased

Use outcomes to improve ranking while preserving explicit preference history and avoiding one-style feedback loops.

### Additional acceptance

- no AI recommendation auto-reserves/purchases/sends;
- proposals use canonical availability;
- reason codes resolve to known facts;
- client can correct explicit preferences;
- sensitive/body inferences are prohibited;
- low-data clients fall back to stylist rules;
- stylist remains author of final recommendation.

**Sequencing:** Client Profile + Look Builder + fitting outcomes -> taste memory -> visual index -> Stylist Copilot -> client presentation -> learning loop.

## Premium commercial wave — Private Wardrobe Vault and occasion planning

This is the luxury-clienteling counterpart to FLASHIN's consumer wardrobe. MB16 focuses on a stylist-curated private wardrobe and high-touch occasion planning.

### Private Wardrobe Vault — ADOPT

Client/stylist may record:

- MB16 purchase;
- externally owned luxury piece;
- photo;
- brand/category;
- colour/material where known;
- size/fit note;
- season;
- client-confirmed status;
- stylist note;
- care/service reference;
- privacy state.

External owned items are clearly distinguished from MB16 catalog products.

### Stylist-curated Wardrobe Memory — ADOPT

The stylist can organise items into:

- core wardrobe;
- seasonal;
- travel;
- occasion;
- rarely used;
- alteration/service needed;
- archive.

These are clienteling labels, not hidden consumer scores.

### Occasion Brief — ADOPT

Create a structured brief:

- occasion/event;
- date/location;
- dress code;
- client's stated objective/preferences;
- existing wardrobe candidates;
- products to source;
- appointment/fitting deadline.

Then:

occasion -> wardrobe review -> proposed looks -> gaps -> showroom pull/hold -> fitting -> final selection

### Wardrobe Gap / Opportunity — ADOPT

Identify explainable gaps such as:

- no suitable shoe/bag/jacket for approved look;
- missing layer/colour balance;
- unavailable size alternative;
- replacement/service need.

This becomes a stylist sales opportunity only after human review.

### Travel Packing / Capsule — ADOPT

For client-approved travel context:

- trip dates;
- activities/dress codes;
- selected wardrobe;
- proposed packing list;
- missing pieces;
- weather only from an approved external source if integrated.

Do not collect precise travel details beyond what the client chooses to share.

### Private Share / Concierge Handoff — ADOPT

Approved wardrobe/look plans can be shared through existing expiring client links.

Never expose the full private wardrobe by default.

### Additional acceptance

- external owned items are not represented as MB16 stock;
- client/stylist provenance of each preference/note is visible;
- occasion recommendations require stylist approval;
- share links expose only selected items;
- private wardrobe can be fully removed/exported according to account policy;
- opportunity analytics do not become hidden pressure scoring.

**Sequencing:** Client Profile + Look Builder + Stylist Copilot -> Wardrobe Vault -> occasion brief -> gap planning -> travel/capsule -> concierge follow-up.

**Commercial framing:** MB16 becomes a private digital wardrobe and personal-shopping operating system for high-value clients.

## Premium enterprise wave — private events and trunk-show clienteling

This wave adds a high-value luxury retail scenario around invitation-only appointments and temporary curated assortments without turning MB16 into a general event platform.

### Private Event Authority — ADOPT

Create:

- event/trunk-show ID;
- title/theme;
- venue;
- start/end;
- host/stylist;
- client segment/eligibility;
- capacity;
- RSVP state;
- private assortment/look selection;
- fitting slots;
- notes/status.

Examples:

- new collection preview;
- trunk show;
- private fitting evening;
- travelling showroom;
- VIP capsule presentation.

### Curated Event Assortment — ADOPT

For each event, define:

- products/variants;
- looks;
- event-only preview items;
- sample/size availability;
- reserve/hold rules;
- event notes.

Canonical product/price/availability remains in MB16 product authority.

### Guest List / RSVP — ADOPT

Track:

invited -> accepted/declined -> appointment selected -> attended/no-show -> follow-up

Respect client contact consent and event privacy.

### Stylist Preparation — ADOPT

Before event:

guest -> taste/profile -> proposed looks/items -> physical preparation -> fitting slot -> staff owner

Reuse the existing Fitting Preparation Board and Stylist Copilot rather than creating separate styling logic.

### Event-day Check-in — ADOPT

Use existing QR/check-in capability where useful.

A check-in may open:

- guest profile summary;
- prepared looks;
- reserved/held items;
- appointment slot.

QR carries opaque IDs only.

### Event Conversion / Follow-up — ADOPT

Measure:

- invite-to-RSVP;
- RSVP-to-attendance;
- attendance-to-fitting;
- fitting-to-hold;
- hold-to-purchase;
- post-event follow-up.

Do not rank clients by hidden wealth/importance scores.

### Additional acceptance

- event assortment references canonical products;
- RSVP never creates stock hold automatically;
- guest list is ACL-protected;
- stylist preparation reuses normal fitting/hold authority;
- event conversion is reproducible from real appointments/holds/orders;
- event mode can be disabled without changing ordinary MB16 clienteling.

**Sequencing:** Client Profile + Appointment + Hold + Look Builder -> Private Event -> RSVP -> preparation/check-in -> event conversion.

**Commercial framing:** this lets MB16 support premium trunk shows and invitation-only selling as a complete clienteling workflow.

## Moat wave — white-label multi-brand clienteling SaaS

This wave turns MB16 from one luxury showroom product into a reusable B2B SaaS platform for boutiques, independent brands, showrooms and private-client teams.

### Organisation / Tenant Authority — ADOPT

Create a strict tenant boundary:

- organisation/brand;
- users/stylists;
- locations/showrooms;
- catalog source;
- client ownership;
- appointment/hold policies;
- branding/theme;
- feature flags;
- integration credentials;
- retention/privacy policy.

No client/profile/order/wardrobe data may cross tenants unless an explicit cross-brand programme exists and the client has opted in.

### White-label Experience — ADOPT

Allow per-tenant:

- logo;
- typography/theme tokens;
- domain/subdomain;
- welcome/concierge text;
- selected navigation;
- language;
- contact/booking routing.

Do not fork the application per client.

One codebase, one release discipline, tenant-scoped configuration.

### Catalog Connector Contract — ADOPT

Define a stable adapter boundary for:

- CSV/Excel import;
- REST/GraphQL commerce feed;
- ERP/PLM connector;
- manual curated catalog;
- optional Synth-v2 handoff/integration.

Canonical MB16 product/clienteling projection stores:

- external provider;
- external product/variant ID;
- sync version/time;
- source status;
- mapping state.

External catalog remains source for facts it owns.

### Client Data Ownership Policy — ADOPT

Each tenant configures:

- client account owner;
- staff visibility;
- location visibility;
- export rules;
- deletion/retention;
- consent scope;
- CRM sync policy.

Do not silently merge the same person across different brand tenants.

### Brand-specific Clienteling Playbooks — ADOPT

Allow versioned playbooks:

- new client onboarding;
- pre-appointment preparation;
- VIP outreach;
- post-fitting follow-up;
- trunk-show follow-up;
- lapsed client reactivation;
- wardrobe review;
- occasion planning.

Playbooks create proposals/tasks/reminders; they do not auto-message without configured approval/consent.

### Tenant Analytics — ADOPT

Provide:

- appointments;
- prepared looks;
- hold-to-purchase;
- stylist follow-up;
- client return;
- event conversion;
- wardrobe/clienteling engagement.

Each tenant sees its own facts plus only explicitly defined anonymised benchmark products if such a service is later created.

### SaaS Commercial Packaging — ADOPT

Possible tiers:

- Solo / stylist;
- Boutique;
- Brand / multi-location;
- Enterprise;
- optional AI Copilot;
- optional Private Events;
- optional Wardrobe Vault;
- optional integrations.

Commercial packaging remains separate from entitlement truth inside product code.

### Additional acceptance

- tenant ID is enforced server-side on every protected entity;
- brand theming cannot change core authority/security logic;
- external catalog mappings are auditable;
- no hidden cross-tenant client graph exists;
- exports/deletions respect tenant/client policy;
- app remains one maintainable product rather than customer forks.

**Sequencing:** current clienteling core -> tenant/org boundary -> configuration/theme -> connector contract -> multi-location -> commercial packaging.

**Commercial framing:** MB16 becomes a repeatable luxury clienteling SaaS product that can be sold to many brands and boutiques instead of one bespoke implementation.

