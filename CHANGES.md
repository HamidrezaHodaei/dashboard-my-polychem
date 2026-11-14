# تغییرات

## فرانت (front/)
- حذف شود: `app/pages/tasks/drafts.vue` (این فایل را از پروژه پاک کنید)
- `app/components/tasks/TaskWorkspaceShell.vue`: اصلاح جهت فلش‌های تقویم، الگوی واکنش‌گرای جدید تقویم، نمای گانت، حذف بخش پیش‌نویس
- `app/stores/taskWorkspace.ts`: حذف بخش `drafts` و `publishTask`
- `app/stores/crm.ts`, `app/components/crm/CrmCustomerPicker.vue`, `app/pages/crm/sales.vue`: نمایش و جستجوی شرکت/برند

## بک‌اند (backend/)
- `app/modules/crm/services.py`: جستجوی کلمه‌به‌کلمه (نام کامل، برند، نیم‌فاصله)، فیلدهای `company` و `label`، نام شرکت کنار شخص در نمودارها
- `app/modules/export_rows.py`: ستون مشتری در خروجی فروش با برچسب «شخص — شرکت»
- `tests/modules/crm/test_crm_sales.py`: سه تست جدید (اجرا نشده؛ محیط من SQLAlchemy/pytest نداشت)
