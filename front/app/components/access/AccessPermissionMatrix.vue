<script setup lang="ts">
// جدول مجوزهای بخش‌ها برای مدیریت دسترسی نقش‌ها و کاربران.
// وضعیت ویرایش را از والد می‌گیرد و فقط تغییرات را نمایش می‌دهد.

import type { MatrixCellMeta, MatrixDraft, MatrixModule } from '~/types/access'

const props = defineProps<{
  modules: MatrixModule[]
  modelValue: MatrixDraft
  meta: Record<string, Record<string, MatrixCellMeta>>
  mode: 'role' | 'user'
  disabled?: boolean
}>()
const emit = defineEmits<{ (e: 'update:modelValue', value: MatrixDraft): void }>()

const BASE_COLUMNS = [
  { action: 'read', label: 'مشاهده' },
  { action: 'create', label: 'ایجاد' },
  { action: 'update', label: 'ویرایش' },
  { action: 'delete', label: 'حذف' },
]
// Extra columns appear only when some row offers them (logistics rows add «بررسی» = approve / reject / suspend).
const EXTRA_COLUMNS = [
  { action: 'review', label: 'بررسی' },
  { action: 'approve', label: 'تأیید' },
  { action: 'reject', label: 'رد' },
  { action: 'dispatch', label: 'ارسال نمونه' },
  { action: 'follow_up', label: 'پیگیری' },
  { action: 'feedback', label: 'بازخورد' },
  { action: 'convert', label: 'تبدیل به فروش' },
  { action: 'export', label: 'خروجی Excel/Word' },
  { action: 'print', label: 'چاپ' },
]
const columns = computed(() => [
  ...BASE_COLUMNS,
  ...EXTRA_COLUMNS.filter(c => props.modules.some(m => m.actions.includes(c.action))),
])
const actionsOf = (moduleKey: string) => props.modules.find(m => m.key === moduleKey)?.actions ?? []
const has = (moduleKey: string, action: string) => actionsOf(moduleKey).includes(action)

function get(moduleKey: string, action: string) {
  return !!props.modelValue[moduleKey]?.[action]
}
function set(moduleKey: string, action: string, value: boolean) {
  emit('update:modelValue', {
    ...props.modelValue,
    [moduleKey]: { ...props.modelValue[moduleKey], [action]: value },
  })
}
function rowAll(moduleKey: string) {
  return actionsOf(moduleKey).every(a => get(moduleKey, a))
}
function setRow(moduleKey: string, value: boolean) {
  emit('update:modelValue', {
    ...props.modelValue,
    [moduleKey]: Object.fromEntries(actionsOf(moduleKey).map(a => [a, value])),
  })
}
function colAll(action: string) {
  return props.modules.filter(m => m.actions.includes(action)).every(m => get(m.key, action))
}
function setCol(action: string, value: boolean) {
  const next: MatrixDraft = {}
  for (const m of props.modules) {
    // rows that don't offer this action are left exactly as they are
    next[m.key] = m.actions.includes(action) ? { ...props.modelValue[m.key], [action]: value } : { ...props.modelValue[m.key] }
  }
  emit('update:modelValue', next)
}

function hint(moduleKey: string, action: string): string {
  const m = props.meta[moduleKey]?.[action]
  if (!m) return ''
  const checked = get(moduleKey, action)
  if (props.mode === 'role') return m.scoped && checked ? 'scoped' : ''
  if (m.direct === 'DENY' && !checked) return 'denied'
  if (m.direct === 'DENY' && checked) return 'unsaved'
  if (m.direct === 'ALLOW' && checked) return 'direct'
  if (m.from_role && checked) return 'role'
  return ''
}
function hintLabel(moduleKey: string, action: string): string {
  const labels: Record<string, string> = { role: 'نقش', direct: 'مستقیم', denied: 'ردشده', scoped: 'محدود به دامنه', unsaved: 'ذخیره‌نشده' }
  return labels[hint(moduleKey, action)] || ''
}

function hintTitle(moduleKey: string, action: string): string {
  const m = props.meta[moduleKey]?.[action]
  const h = hint(moduleKey, action)
  if (h === 'role') return `از نقش: ${(m?.role_names || []).join(', ')}`
  if (h === 'direct') return 'مستقیماً به این کاربر اعطا شده است'
  if (h === 'denied') return 'برای این کاربر صریحاً رد شده است (بر نقش‌ها اولویت دارد)'
  if (h === 'scoped') return 'فقط در دامنهٔ محدود (سازمان / دپارتمان / تیم) اعطا شده است'
  return ''
}
</script>

<template>
  <div class="overflow-x-auto">
    <table class="w-full text-sm">
      <thead>
        <tr class="border-b bg-muted/40 text-left text-muted-foreground">
          <th class="px-4 py-3 font-medium">
            بخش
          </th>
          <th v-for="c in columns" :key="c.action" class="px-4 py-3 text-center font-medium">
            <div class="flex flex-col items-center gap-1.5">
              <span>{{ c.label }}</span>
              <Checkbox
                :model-value="colAll(c.action)"
                :disabled="disabled"
                :title="`تغییر ${c.label} برای همهٔ بخش‌ها`"
                @update:model-value="setCol(c.action, $event === true)"
              />
            </div>
          </th>
          <th class="px-4 py-3 text-center font-medium">
            همه
          </th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="m in modules" :key="m.key" class="border-b last:border-0 hover:bg-muted/20">
          <td class="px-4 py-3">
            <p class="font-medium">
              {{ m.label }}
            </p>
            <p class="font-mono text-xs text-muted-foreground">
              {{ m.key }}.*
            </p>
          </td>
          <td v-for="c in columns" :key="c.action" class="px-4 py-3 text-center">
            <span v-if="!has(m.key, c.action)" class="text-muted-foreground/50" aria-hidden="true">—</span>
            <div v-else class="flex flex-col items-center gap-1">
              <Checkbox
                :model-value="get(m.key, c.action)"
                :disabled="disabled"
                @update:model-value="set(m.key, c.action, $event === true)"
              />
              <span
                v-if="hint(m.key, c.action)"
                :title="hintTitle(m.key, c.action)"
                class="rounded px-1.5 text-[10px] font-medium uppercase tracking-wide"
                :class="{
                  'bg-blue-500/10 text-blue-600 dark:text-blue-400': hint(m.key, c.action) === 'role',
                  'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400': hint(m.key, c.action) === 'direct',
                  'bg-destructive/10 text-destructive': hint(m.key, c.action) === 'denied',
                  'bg-amber-500/10 text-amber-600': hint(m.key, c.action) === 'scoped' || hint(m.key, c.action) === 'unsaved',
                }"
              >{{ hintLabel(m.key, c.action) }}</span>
            </div>
          </td>
          <td class="px-4 py-3 text-center">
            <Checkbox
              :model-value="rowAll(m.key)"
              :disabled="disabled"
              @update:model-value="setRow(m.key, $event === true)"
            />
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
