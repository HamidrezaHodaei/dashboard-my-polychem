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
