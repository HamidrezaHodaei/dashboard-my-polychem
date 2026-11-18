# Purchase Reports (گزارشات خرید) — backend

`/api/purchases`, module `app/modules/purchases`, migrations `c4e8a2f6b9d1` (first release), `d5f9b3a7c1e2` (catalog + finance step) and `e6a1c4d8f2b3` (review status + direct purchases); run `flask db upgrade`.

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

## Revision 2 (corrections)
* Statuses: new `SENT_TO_FINANCE` («ارسال به مالی»). The existing values keep their codes but are relabelled: `AWAITING_DELIVERY` = «در حال تحویل و حمل», `COMPLETED` = «پایان‌یافته»; «در حال استعلام» = `INQUIRING`.
  Flow: … → PURCHASING → `POST /<id>/send-to-finance` → SENT_TO_FINANCE → result saved → AWAITING_DELIVERY / COMPLETED. The final result step now requires "sent to finance"; changing the selected supplier/prices afterwards needs a send-back and a new send to finance.
* Product catalog `purchase_products` (own table): `name` unique, `code` String(64) typed by the admin (letters/digits/`- _ . / \ + # ( ) [ ]`, unique, leading zeros kept, never generated or numeric). Items must pick a product (`product_id`); name and code are copied onto the item. Permission `procurement.purchase.manage_catalog` (admin). `GET/POST /products`, `PATCH/DELETE /products/<id>` (delete only if unused — deactivate otherwise).
* Units: free text on the item (any value, whitespace tidied); `GET /units?q=` returns earlier values, most used first, as suggestions only.
* Prices: whole rials. Price fields reject fractions; stored as plain numbers; Excel exports mark money columns «(ریال)» and format them `#,##0` (cell value stays numeric).

## Revision 3
* Request numbers are typed by the expert (`request_no` in step 1): required, ≤30 chars, unique (case-insensitive), editable later (audited). Nothing is auto-numbered; existing numbers are kept.
* Review status (cartable) = new column `review_status`, separate from the workflow `status`: PENDING_REVIEW (default) / APPROVED / REJECTED / NEEDS_REVISION, set by anyone with `update` through `POST /<id>/review {status, note}` (note required for REJECTED / NEEDS_REVISION). The expert may pick NEEDS_REVISION directly. Rejected requests stay (list, filter `review_status=`, dashboard, exports) but are frozen for editing until the status is changed, and are not counted as «open». The older workflow status NEEDS_REVISION («ارسال برای اصلاح» by an approver) is unchanged and independent.
* Direct purchases: table `purchase_direct`, `GET/POST /direct`, `PUT/DELETE /direct/<id>`; fields doc_no (typed, unique), purchase_date, title, supplier (bank or free name), amount (whole rials), usage_place, optional group/description. They add to «spent», the trend, the group table and the supplier table, and have their own export (`kind=direct`). Filters that exist only on requests (status, review status, unit, request number) leave them out; date / group / supplier / item filters apply.
* Dashboard: `review_counts` (all requests incl. drafts, under every filter except the review one), `kpis.direct`, `kpis.spent.{requests_amount,direct_amount}`, group `direct_count/direct_spent`, supplier `direct_count/direct_amount`, trend `direct_spent`.
