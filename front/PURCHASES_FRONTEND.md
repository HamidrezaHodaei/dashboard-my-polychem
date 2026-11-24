# Purchase Reports — frontend (Nuxt)
New sidebar tab: «تدارکات و لجستیک» ← «گزارشات خرید» (`/procurement/purchases`, nav key `purchase_reports`). Requires the backend migration c4e8a2f6b9d1.

New files: `app/pages/procurement/purchases/index.vue` (filters, 6 KPIs with drill-down, charts, commodity groups, list, exports),
`app/pages/procurement/purchases/[id].vue` (6-step wizard; `/new` for a new purchase), `app/components/purchases/{Field,Money,Files,Bars,Line}.vue`,
`app/stores/purchases.ts`, `app/utils/purchase.ts`.
Changed: `app/components/layout/LayoutSidebar.vue` (menu item), `app/middleware/auth.global.ts` (route guard key).
Not built/type-checked here (no node_modules): run `pnpm install && pnpm build` first.

## Revision 2
* `Stepper.vue`: life-cycle stepper (ثبت اطلاعات → در حال استعلام → انتخاب تأمین‌کننده → انجام خرید → ارسال به مالی → در حال تحویل و حمل → پایان‌یافته). Built with `dir="rtl"`: the first step is on the right and the coloured line is anchored to the right edge and grows leftwards; on phones it scrolls sideways instead of shrinking. The wizard's own step bar fills right-to-left too (the old shadcn `Progress` filled left-to-right).
* `ProductPicker.vue` (items come from the catalog), `Unit.vue` (free-text unit with searchable suggestions), `pages/procurement/purchases/products.vue` (admin catalog, shown only with `manage_catalog`).
* `money()` now prints `1,500,000,000 ریال`; `PurchasesMoney rial` shows the separators and a «ریال» tag while typing (the model stays a plain number).

## Revision 3
Index page: review-status chips (cartable) + filter, review column (click to set the status), «خریدهای مستقیم» tab / KPI card / dialog. Wizard: editable request number, «تعیین وضعیت بررسی». New components `ReviewDialog.vue`, `DirectDialog.vue`.

## Revision 4 — item-based flow
* **انبار** (`/inventory`) is ONE page now (all sub-tabs and their placeholder pages removed): request list with per-item badges, «ثبت درخواست خرید» (`/inventory/new`), detail `/inventory/[id]`.
* **مالی** (`/finance`) is ONE page: «در انتظار پرداخت» / «پرداخت‌شده» queues, detail `/finance/[id]` (cash / cheque form, «ارجاع به تدارکات»). The old mock finance pages were removed.
* **گزارشات خرید** (`/procurement/purchases`): tabs کارتابل تدارکات · تأیید مدیر · همهٔ درخواست‌ها · گزارش مدیریتی و تنظیمات; detail `/procurement/purchases/flow/[id]`. The previous screens moved to `/procurement/purchases/legacy` (+ direct purchases).
* New: `utils/purchaseFlow.ts`, `stores/purchaseFlow.ts`, `components/purchases/Flow{Badge,Form,List,Detail,Page,Report}.vue`. Changed: `LayoutSidebar.vue` (انبار / مالی are single links gated by `purchase_warehouse` / `purchase_finance`), `auth.global.ts`, `products.vue` (+ unit), `DashboardOperations.vue` (demo links).
* Not built / type-checked here (no node_modules, no network): run `pnpm install && pnpm build`.

## Revision 5 — menus + Dark Mode
* Sidebar: «انبار» → submenu «درخواست خرید» (`/inventory`), «مالی» → submenu «درخواست پرداخت» (`/finance`); same routes, `navKey`s (`purchase_warehouse` / `purchase_finance`) and permissions.
* Dark mode is fixed in ONE place: `app/assets/css/main.css` (`@layer base`: `color-scheme`, native `<select>` list / options / arrow, placeholder, focus ring, autofill, date icon — all via tokens) and `app/assets/css/dark-compat.css`.
* `dark-compat.css` is GENERATED (`python3 scripts/gen-dark-compat.py`): it re-maps light-only palette classes (`bg-emerald-100`, `text-amber-800`, `border-red-200`, `hover:bg-*-50`, `bg-white`…) to palette-derived dark colors, so every badge / status / alert / table cell that used them is readable in dark mode with no per-component edits. An element that already carries its own `dark:bg-*|text-*|border-*` class is left alone. No `!important`.
* Flow components: links / attachments use `text-blue-700 dark:text-blue-300`.
* NOT verified in a browser (no node / network here): open payment + inquiry tabs, an open native select, a table row hover in both themes.

## Revision 6 — request dashboard, menus, one entry for «ثبت خرید»
* **Sidebar «انبار»** (no icons, like the other submenus): «داشبورد درخواست خرید» `/inventory/dashboard` · «درخواست خرید» `/inventory` · «ثبت درخواست خرید» `/inventory/new`. Same `purchase_warehouse` key; routes and permissions unchanged (the guard is prefix based). `/inventory/new` shows a notice when the user lacks the warehouse permission.
* **Dashboard** (`pages/inventory/dashboard.vue`, `components/purchases/FlowDashboard.vue`): key figures, status distribution, «نیازمند توجه» and «آخرین درخواست‌ها». Every figure links to the list filtered on it. It uses only existing endpoints (`/purchases/flow/requests`, `/kpi`) — a block whose endpoint the user may not read is left out. If the status counts ever need to be cheaper, add one aggregated `GET /purchases/flow/stats`; the component would then replace the 8 count requests.
* **List** (`FlowList.vue`): status chips instead of a select, `?status=` / `?queue=open` in the URL (opt-in with `sync-query`), items collapsed after three, request number is a real link.
* **Request form** (`FlowForm.vue`): same payload and validation; fewer inputs per line (code / group / unit shown as note or read-only), the submit bar is sticky, add-item button at the end of the list.
* **گزارشات خرید** (`/procurement/purchases`): «ثبت خرید جدید» (the 6-step wizard, `/procurement/purchases/new`) is started ONLY from here and was removed from the old-records page. Old records stay at `/procurement/purchases/legacy` (button «سوابق قبلی و خرید مستقیم» + back link); **خرید مستقیم is untouched**. Tabs are kept in `?tab=`; «مدیریت کالاها» moved into the ⋮ menu. No data, route or API was removed.
* Not built / type-checked here (no node_modules, no network): run `pnpm install && pnpm build`.
