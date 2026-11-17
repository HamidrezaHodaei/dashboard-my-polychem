# Purchase Reports (گزارشات خرید) — backend

`/api/purchases`, module `app/modules/purchases`, migration `c4e8a2f6b9d1` (down_revision `b2d4f6a8c0e3`, the current single head).

    flask db upgrade
    pytest tests/modules/purchases      # written, NOT yet executed (see "Status")

## Tables
`purchase_requests`, `purchase_items`, `purchase_inquiries`, `purchase_inquiry_items`, `purchase_events`, `purchase_files`.
Commodity groups = active MAIN categories of `supplier_categories` (nothing hardcoded; the item stores `category_id` + a name snapshot).
Suppliers for quotations come from `suppliers`.

## Permissions (GLOBAL scope, enforced in services.py)
`procurement.purchase.{read,create,update,delete,approve,export}` — all non-delegable. Nav key `purchase_reports`.
`approve` = approve a reference price, send a request back for revision / reopen a closed one. `delete` = drafts and cancelled only.
Seeded: admin (all), roles `purchase_manager`, `purchase_expert` (read/create/update/export), `purchase_viewer`. Existing roles (e.g. procurement_manager) are untouched — grant them in the matrix.

## Workflow
DRAFT → ENTERING (step 1 complete) → AWAITING_INQUIRY (`POST /submit`, steps 1-3 valid) → INQUIRING → AWAITING_SELECTION (inquiries finalized)
→ PURCHASING (supplier selected) → AWAITING_DELIVERY → COMPLETED (fully delivered). Any open status → CANCELLED (reason). `send-back` → NEEDS_REVISION.
Every step save and status change goes to `purchase_events` (user + time); price / supplier / status / final-data changes also to `audit_logs` (module `procurement`).

## Rules implemented
* max 3 inquiries; fewer than 3 → `shortfall_reason` required to finalize; one inquiry per supplier; unit price per item per inquiry.
* lowest = smallest total (items + extra costs) among inquiries priced for ALL items; selecting another one requires `note`; ≥1 reason always.
* items cannot be added/removed once inquiries exist; no inquiry edits after the purchase is recorded; re-pricing the chosen quotation clears the selection.
* final amount is computed server-side: Σ(final unit price × purchased qty) + extra costs.
* savings = (APPROVED reference unit price − final unit price) × purchased qty, COMPLETED requests only; items without an approved reference are excluded and counted (`items_without_reference`); negatives stay negative.
* next-month budget = open requests whose required date is in the next Jalali month; amount = agreed prices → items' estimates → request budget; requests with none are counted as `unpriced_count`.

## Endpoints
meta, suppliers?q=, files (POST/GET), list (`filters`, `sort`, `direction`, `page`, `kpi=total|completed|open|spent|savings|next_month`), create, `GET /<id>`,
`PUT /<id>/basic|items|budget|inquiries|selection|result` (`complete:true` validates the step), `POST /<id>/submit|cancel|send-back|approve-reference`, `DELETE /<id>`,
`GET /dashboard`, `GET /export?kind=overview|groups|requests|inquiries|suppliers|costs|all&format=xlsx|json`.
Filters (all combinable, shared by list/dashboard/export): `date_from, date_to, category_id, status (comma list), supplier, supplier_id, unit, request_no, item, granularity`.

## Status
Authored in an environment without SQLAlchemy/Node: Python was compile-checked only; tests and the Nuxt build were not run.
PDF = the browser's print dialog («Save as PDF»), as in the other modules (no Persian-capable PDF library/font in requirements.txt).
