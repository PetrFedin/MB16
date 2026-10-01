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
