<script setup lang="ts">
import type { UserRole } from '~/stores/auth'

const auth = useAuthStore()
const settings = useSettingsStore()
const notify = useNotify()

const roleLabel: Record<UserRole, string> = { admin: 'Administrator', manager: 'Manager', accountant: 'Accountant', user: 'User' }
const actions = [
  { key: 'view', label: 'View' },
  { key: 'create', label: 'Create' },
  { key: 'edit', label: 'Edit' },
  { key: 'delete', label: 'Delete' },
  { key: 'reports', label: 'Reports' },
] as const

// Demo permission matrix, editable locally (wire to a real RBAC endpoint later).
const permissions = reactive<Record<UserRole, Record<string, boolean>>>({
  admin: { view: true, create: true, edit: true, delete: true, reports: true },
  manager: { view: true, create: true, edit: true, delete: false, reports: true },
  accountant: { view: true, create: true, edit: true, delete: false, reports: true },
  user: { view: true, create: false, edit: false, delete: false, reports: false },
})

function updateCurrency(unit: 'toman' | 'rial') {
  settings.setCurrencyUnit(unit)
  notify.success(unit === 'toman' ? 'Currency changed to toman.' : 'Currency changed to rial.')
}
</script>

<template>
  <div class="mx-auto max-w-3xl space-y-6">
    <div>
      <h1 class="text-xl font-bold text-ink-900">تنظیمات</h1>
      <p class="mt-1 text-sm text-ink-700/60">Profile, currency, and access levels</p>
    </div>

    <div class="rounded-xl border border-paper-200 bg-white p-5 shadow-card">
      <h2 class="mb-3 text-sm font-semibold text-ink-900">پروفایل من</h2>
      <div class="flex items-center gap-3">
        <div class="flex h-11 w-11 items-center justify-center rounded-full bg-ink-800 text-sm font-semibold text-white">
          {{ auth.user?.name.slice(0, 2) }}
        </div>
        <div>
          <p class="text-sm font-medium text-ink-900">{{ auth.user?.name }}</p>
          <p class="text-xs text-ink-700/60">{{ auth.user ? roleLabel[auth.user.role] : '—' }}</p>
        </div>
      </div>
    </div>

    <div class="rounded-xl border border-paper-200 bg-white p-5 shadow-card">
      <h2 class="mb-3 text-sm font-semibold text-ink-900">Currency</h2>
      <div class="flex gap-2">
        <button
          class="flex-1 rounded-lg border py-2.5 text-sm font-medium"
          :class="settings.currencyUnit === 'toman' ? 'border-gain-600 bg-gain-50 text-gain-700' : 'border-paper-200 text-ink-700/60'"
          @click="updateCurrency('toman')"
        >تومان</button>
        <button
          class="flex-1 rounded-lg border py-2.5 text-sm font-medium"
          :class="settings.currencyUnit === 'rial' ? 'border-gain-600 bg-gain-50 text-gain-700' : 'border-paper-200 text-ink-700/60'"
          @click="updateCurrency('rial')"
        >ریال</button>
      </div>
      <p class="mt-2 text-xs text-ink-700/50">This currency is used as the default amount display throughout the panel.</p>
    </div>

    <div class="overflow-x-auto rounded-xl border border-paper-200 bg-white shadow-card">
      <div class="border-b border-paper-100 p-5 pb-3">
        <h2 class="text-sm font-semibold text-ink-900">نقش‌ها و سطوح دسترسی</h2>
      </div>
      <table class="w-full min-w-[520px] text-right text-sm">
        <thead>
          <tr class="border-b border-paper-200 text-xs text-ink-700/60">
            <th class="px-5 py-3 font-medium">نقش</th>
            <th v-for="a in actions" :key="a.key" class="px-3 py-3 text-center font-medium">{{ a.label }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(perms, role) in permissions" :key="role" class="border-b border-paper-100 last:border-0">
            <td class="px-5 py-3 font-medium text-ink-900">{{ roleLabel[role as UserRole] }}</td>
            <td v-for="a in actions" :key="a.key" class="px-3 py-3 text-center">
              <input v-model="perms[a.key]" type="checkbox" class="h-4 w-4 rounded border-paper-200 text-gain-600 focus:ring-gain-400">
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
