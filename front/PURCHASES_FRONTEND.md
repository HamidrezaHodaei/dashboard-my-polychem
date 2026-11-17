# Purchase Reports — frontend (Nuxt)
New sidebar tab: «تدارکات و لجستیک» ← «گزارشات خرید» (`/procurement/purchases`, nav key `purchase_reports`). Requires the backend migration c4e8a2f6b9d1.

New files: `app/pages/procurement/purchases/index.vue` (filters, 6 KPIs with drill-down, charts, commodity groups, list, exports),
`app/pages/procurement/purchases/[id].vue` (6-step wizard; `/new` for a new purchase), `app/components/purchases/{Field,Money,Files,Bars,Line}.vue`,
`app/stores/purchases.ts`, `app/utils/purchase.ts`.
Changed: `app/components/layout/LayoutSidebar.vue` (menu item), `app/middleware/auth.global.ts` (route guard key).
Not built/type-checked here (no node_modules): run `pnpm install && pnpm build` first.
