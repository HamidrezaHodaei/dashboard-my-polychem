# Logistics frontend (Nuxt) — بانک اطلاعات لجستیک

New tab: سایدبار ← «تدارکات و لجستیک» ← «بانک اطلاعات لجستیک»  (route `/procurement/logistics`).
Requires the logistics backend (migration a7c3e9d1f5b2) to be installed first.

New files
- app/pages/procurement/logistics/index.vue   list, type tabs, filters, detail, review, delete
- app/components/logistics/FormWizard.vue     the wizard (add + edit)
- app/components/logistics/Field.vue, Checklist.vue
- app/stores/logistics.ts                     API calls + per-type permission helpers
- app/utils/logistics-form.ts                 steps, validation (mirrors backend), payload mapping

Changed files (2 small edits, see the .patch)
- app/components/layout/LayoutSidebar.vue     new menu item
- app/middleware/auth.global.ts               route guard accepts several alternative keys

Wizard: step 1 picks شرکت حمل‌ونقل / راننده.
 Company: اطلاعات شرکت → نماینده و تماس → محدوده فعالیت
 Driver : اطلاعات هویتی → اطلاعات تماس → وسیله نقلیه و بارگیر → محدوده فعالیت
The vehicle step exists only on the driver path. All option lists come from
GET /api/logistics/public/reference. On "next" a new record's step is also checked by the
server (duplicate national code / mobile show up immediately).
Buttons (add/edit/review/delete) and tabs appear only for the applicant types the user has
permissions for (`logistics.company.*` / `logistics.driver.*`); the server enforces the same.
