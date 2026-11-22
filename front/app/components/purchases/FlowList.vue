<!-- <PurchasesFlowList base="/inventory" queue="" /> : searchable list of flow requests with per-item badges.
     A row opens `${base}/${id}`. `queue` = manager | finance | finance_done | open | '' (all). -->
<template>
  <div class="space-y-4">
    <div class="flex flex-wrap items-center gap-2">
      <Input v-model="q" placeholder="جستجوی شماره درخواست، درخواست‌کننده یا کالا…" class="w-72" @keyup.enter="reload" />
      <select v-if="!queue || queue === 'open'" v-model="status" class="h-9 rounded-md border border-input bg-transparent px-3 text-sm" @change="reload">
        <option value="">همه وضعیت‌ها</option>
        <option v-for="s in store.meta?.request_statuses" :key="s.value" :value="s.value">{{ s.label }}</option>
      </select>
      <select v-model="unit" class="h-9 rounded-md border border-input bg-transparent px-3 text-sm" @change="reload">
        <option value="">همه واحدها</option>
        <option v-for="u in store.meta?.units" :key="u" :value="u">{{ u }}</option>
      </select>
      <Button variant="outline" size="sm" @click="reload">جستجو</Button>
      <span class="mr-auto text-xs text-muted-foreground">{{ total }} درخواست</span>
    </div>
    <p v-if="error" class="rounded-lg border border-destructive/40 bg-destructive/5 p-3 text-sm text-destructive">{{ error }}</p>
    <div class="overflow-x-auto rounded-xl border">
      <table class="w-full min-w-[820px] text-sm">
        <thead class="bg-muted/50 text-xs text-muted-foreground">
          <tr><th class="p-3 text-right">شماره</th><th class="p-3 text-right">واحد / درخواست‌کننده</th><th class="p-3 text-right">تاریخ ثبت / نیاز</th><th class="p-3 text-right">وضعیت درخواست</th><th class="p-3 text-right">وضعیت اقلام</th></tr>
        </thead>
        <tbody>
          <tr v-if="loading"><td colspan="5" class="p-6 text-center text-muted-foreground">در حال بارگذاری…</td></tr>
          <tr v-else-if="!rows.length"><td colspan="5" class="p-6 text-center text-muted-foreground">درخواستی پیدا نشد.</td></tr>
          <tr v-for="r in rows" :key="r.id" class="cursor-pointer border-t align-top hover:bg-muted/40" @click="navigateTo(`${base}/${r.id}`)">
            <td class="p-3 font-semibold" dir="ltr">{{ r.request_no }}</td>
            <td class="p-3">{{ r.requester_unit }}<div class="text-xs text-muted-foreground">{{ r.requester_name }}</div></td>
            <td class="p-3 text-xs">{{ r.request_date_jalali }}<div class="text-muted-foreground">نیاز: {{ r.required_date_jalali }}</div></td>
            <td class="p-3">
              <PurchasesFlowBadge kind="request" :value="r.status" :label="r.status_label" />
              <div v-if="r.overdue_items" class="mt-1 text-xs text-red-600">{{ r.overdue_items }} قلم دارای تأخیر</div>
              <div v-if="r.missing_receipts" class="mt-1 text-xs text-orange-600">{{ r.missing_receipts }} قلم بدون رسید انبار</div>
            </td>
            <td class="p-3">
              <ul class="space-y-1">
                <li v-for="i in r.items" :key="i.id" class="flex items-center gap-2">
                  <PurchasesFlowBadge kind="item" :value="i.status" :label="i.status_label" />
                  <span class="truncate">{{ i.name }}</span>
                  <span v-if="i.receipt_missing" class="rounded bg-orange-100 px-1.5 text-[11px] text-orange-800">بدون رسید</span>
                  <span v-if="i.overdue" class="rounded bg-red-100 px-1.5 text-[11px] text-red-700">تأخیر</span>
                </li>
              </ul>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    <div v-if="total > perPage" class="flex items-center justify-center gap-3 text-sm">
      <Button variant="outline" size="sm" :disabled="page <= 1" @click="go(page - 1)">قبلی</Button>
      <span>{{ page }} / {{ Math.ceil(total / perPage) }}</span>
      <Button variant="outline" size="sm" :disabled="page * perPage >= total" @click="go(page + 1)">بعدی</Button>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { FlowRow } from '~/stores/purchaseFlow'

const props = defineProps<{ base: string, queue?: string }>()
const store = usePurchaseFlowStore()
const rows = ref<FlowRow[]>([])
const total = ref(0)
const page = ref(1)
const perPage = 15
const loading = ref(false)
const error = ref('')
const q = ref('')
const status = ref('')
const unit = ref('')

let seq = 0
async function load() {
  const id = ++seq
  loading.value = true
  error.value = ''
  try {
    const res = await store.list({ queue: props.queue || undefined, q: q.value || undefined, status: status.value || undefined, unit: unit.value || undefined, page: page.value, per_page: perPage })
    if (id !== seq) return
    rows.value = res.items
    total.value = res.total
  }
  catch (e: any) { if (id === seq) { error.value = e?.message || 'بارگذاری فهرست انجام نشد.'; rows.value = [] } }
  finally { if (id === seq) loading.value = false }
}
const reload = () => { page.value = 1; return load() }
const go = (p: number) => { page.value = p; return load() }
watch(() => props.queue, reload)
await store.loadMeta()
onMounted(load)
defineExpose({ reload: load })
</script>
