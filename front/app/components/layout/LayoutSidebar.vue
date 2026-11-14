<template>
  <AppSidebar
    :nav="nav"
  >
    <template #header>
      <LayoutSidebarHeader />
    </template>
    <template #footer>
      <LayoutSidebarFooter />
    </template>
  </AppSidebar>
</template>

<script lang="ts" setup>
import type { SidebarProps } from '@/types/sidebar'

const baseNav: SidebarProps['nav'] = [
  {
    items: [
      {
        title: 'پیشخوان',
        icon: 'lucide:house',
        link: {
          to: '/',
        },
      },
      {
        title: 'ایمیل',
        icon: 'lucide:mail',
        activeRoute: ['/mail'],
        children: [
          {
            title: 'سامانه ایمیل',
            icon: 'lucide:inbox',
            link: {
              to: '/mail',
            },
            activeRoute: ['/mail'],
          },
        ],
      },
      {
        title: 'رویدادها',
        icon: 'lucide:calendar-days',
        link: {
          to: '/events',
        },
      },
    ],
  },
  {
    heading: 'منوی اصلی',
    items: [
      {
        title: 'کارها و وظایف من',
        icon: 'lucide:shopping-bag',
        activeRoute: ['/tasks', '/tasks/your-work', '/tasks/project', '/tasks/views', '/tasks/analytics', '/tasks/archives'],
        children: [
          {
            title: 'فضای کاری',
            link: { to: '/tasks' },
            activeRoute: ['/tasks'],
            navKey: 'tasks',
          },
          {
            title: 'کارتابل واحد',
            link: { to: '/tasks/project' },
            activeRoute: ['/tasks/project'],
            navKey: 'tasks',
          },
          {
            title: 'نماها',
            link: { to: '/tasks/views' },
            activeRoute: ['/tasks/views'],
            navKey: 'tasks',
          },
          {
            title: 'تحلیل‌ها',
            link: { to: '/tasks/analytics' },
            activeRoute: ['/tasks/analytics'],
            navKey: 'task_analytics',
          },
          {
            title: 'بایگانی',
            link: { to: '/tasks/archives' },
            activeRoute: ['/tasks/archives'],
            navKey: 'tasks',
          },
        ],
      },
      {
        title: 'مدیریت فروش و مشتریان',
        icon: 'lucide:badge-dollar-sign',
        activeRoute: ['/crm'],
        children: [
          { title: 'داشبورد فروش', link: { to: '/crm/dashboard' }, navKey: 'crm_dashboard' },
          { title: 'بانک اطلاعات مشتریان', link: { to: '/crm/customers' }, navKey: 'customers' },
          { title: 'فروش‌ها', link: { to: '/crm/sales' }, navKey: 'crm_sales' },
          { title: 'درخواست نمونه محصول', link: { to: '/crm/request-samples' }, navKey: 'request_samples' },
          { title: 'تنظیمات فروش', link: { to: '/crm/settings' }, navKey: 'crm_settings' },
        ],
      },
      {
        title: 'مالی',
        icon: 'lucide:landmark',
        adminOnly: true,
        activeRoute: ['/finance'],
        children: [
          {
            title: 'پیشخوان',
            link: {
              to: '/finance/dashboard',
            },
            activeRoute: ['/finance', '/finance/dashboard'],
          },
          {
            title: 'حساب‌ها',
            link: {
              to: '/finance/accounts',
            },
            activeRoute: ['/finance/accounts'],
          },
          {
            title: 'تراکنش‌ها',
            link: {
              to: '/finance/transactions',
            },
            activeRoute: ['/finance/transactions'],
          },
          {
            title: 'مشتریان',
            link: {
              to: '/finance/customers',
            },
            activeRoute: ['/finance/customers'],
          },
          {
            title: 'طرف‌حساب‌ها',
            link: {
              to: '/finance/parties',
            },
            activeRoute: ['/finance/parties'],
          },
          {
            title: 'خریدها و هزینه‌ها',
            link: {
              to: '/finance/purchases',
            },
            activeRoute: ['/finance/purchases', '/finance/expenses'],
          },
          {
            title: 'گزارش‌ها',
            link: {
              to: '/finance/reports',
            },
            activeRoute: ['/finance/reports'],
          },
          {
            title: 'تنظیمات',
            link: {
              to: '/finance/settings',
            },
            activeRoute: ['/finance/settings'],
          },
        ],
      },
      {
        title: 'انبار',
        icon: 'lucide:warehouse',
        adminOnly: true,
        children: [
          {
            title: 'پیشخوان',
            link: {
              to: '/inventory',
            },
          },
          {
            title: 'موجودی کالا',
            link: {
              to: '/inventory/stock',
            },
          },
          {
            title: 'ورودی انبار',
            link: {
              to: '/inventory/inbound',
            },
          },
          {
            title: 'خروجی انبار',
            link: {
              to: '/inventory/outbound',
            },
          },
          {
            title: 'گردش موجودی',
            link: {
              to: '/inventory/movements',
            },
          },
          {
            title: 'انتقال‌ها',
            link: {
              to: '/inventory/transfers',
            },
          },
          {
            title: 'گزارش‌ها',
            link: {
              to: '/inventory/reports',
            },
          },
          {
            title: 'تنظیمات',
            link: {
              to: '/inventory/settings',
            },
          },
        ],
      },
      {
        title: 'پنل مشتریان',
        icon: 'lucide:panel-top',
        adminOnly: true,
        children: [
          {
            title: 'پیشخوان',
            link: {
              to: '/customer-panel',
            },
          },
          {
            title: 'سفارش‌ها',
            link: {
              to: '/customer-panel/orders',
            },
          },
          {
            title: 'تیکت‌ها',
            link: {
              to: '/customer-panel/tickets',
            },
          },
          {
            title: 'مدیریت کاربران',
            link: {
              to: '/customer-panel/users',
            },
          },
        ],
      },
      {
        title: 'مدیریت وب‌سایت',
        icon: 'lucide:globe',
        adminOnly: true,
        children: [
          {
            title: 'آمار بازدیدکنندگان',
            link: {
              to: '/website/visitor-statistics',
            },
          },
          {
            title: 'وبلاگ',
            link: {
              to: '/website/blog',
            },
          },
          {
            title: 'درخواست نمونه محصول',
            link: {
              to: '/website/product-sample-requests',
            },
          },
        ],
      },
      {
        title: 'تدارکات و لجستیک',
        icon: 'lucide:truck',
        children: [
          {
            title: 'تأمین‌کنندگان',
            link: {
              to: '/procurement/suppliers',
            },
            navKey: 'suppliers',
          },
          {
            title: 'بانک اطلاعات لجستیک',
            link: {
              to: '/procurement/logistics',
            },
            navKey: ['logistics_companies', 'logistics_drivers'],
          },
        ],
      },
      {
        title: 'مدیریت دسترسی',
        icon: 'lucide:shield-check',
        children: [
          {
            title: 'کاربران',
            link: {
              to: '/access-management/users',
            },
            navKey: 'users',
          },
          {
            title: 'نقش‌ها',
            link: {
              to: '/access-management/roles',
            },
            navKey: 'roles',
          },
          {
            title: 'مجوزها',
            link: {
              to: '/access-management/permissions',
            },
            navKey: 'permissions',
          },
          {
            title: 'سازمان‌ها',
            link: {
              to: '/access-management/organizations',
            },
            navKey: 'organizations',
          },
          {
            title: 'تیم‌ها',
            link: {
              to: '/access-management/teams',
            },
            navKey: 'teams',
          },
        ],
      },
      {
        title: 'تنظیمات',
        icon: 'lucide:settings',
        activeRoute: ['/settings'],
        children: [
          {
            title: 'عمومی',
            link: {
              to: '/settings',
            },
          },
          {
            title: 'امنیت',
            link: {
              to: '/settings/security',
            },
          },
          {
            title: 'اعلان‌ها',
            link: {
              to: '/settings/notifications',
            },
          },
        ],
      },
    ],
  },
  {
    heading: 'بیشتر',
    items: [
      {
        title: 'احراز هویت',
        icon: 'lucide:lock',
        adminOnly: true,
        children: [
          {
            title: 'ورود',
            link: {
              to: '/auth/signin',
            },
          },
          {
            title: 'ثبت‌نام',
            link: {
              to: '/auth/signup',
            },
          },
          {
            title: 'بازیابی رمز عبور',
            link: {
              to: '/auth/reset-password',
            },
          },
        ],
      },
    ],
  },
]

// Menu visibility follows the user's access -- an entry the user may not open is not rendered at all:
//  * `navKey`    -> shown only when the backend granted that navigation entry (derived from the user's
//                   permissions, e.g. crm.sale.read -> crm_sales); an array means "any of these";
//  * `adminOnly` -> sections no permission can be granted for (no backend module yet): admins only;
//  * a parent whose children are all hidden is hidden too, and so is a group left without items.
// The route guard (middleware/auth.global.ts) enforces the same rules for typed URLs.
const auth = useAuthStore()
const keyVisible = (key?: string | string[]) => {
  if (!key) return true
  return (Array.isArray(key) ? key : [key]).some(k => auth.navigationKeys.has(k))
}
const nav = computed<SidebarProps['nav']>(() => baseNav
  .map(group => ({
    ...group,
    items: group.items
      .filter(item => !item.adminOnly || auth.isAdmin)
      .map(item => ('children' in item
        ? { ...item, children: item.children.filter(c => (!c.adminOnly || auth.isAdmin) && keyVisible(c.navKey)) }
        : item))
      .filter(item => 'children' in item ? item.children.length > 0 : keyVisible((item as { navKey?: string | string[] }).navKey)),
  }))
  .filter(group => group.items.length > 0))
</script>
