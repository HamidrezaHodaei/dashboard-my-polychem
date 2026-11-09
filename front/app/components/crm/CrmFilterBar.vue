<!-- Filters shared by the CRM dashboard and the sales table. Edits are staged in `draft` and only
     written to the store (which feeds table + KPIs + charts) on "اعمال فیلترها", so every view
     always describes exactly the same set of sales. Dates are Jalali in the UI, ISO on the wire. -->
<template>
  <Card class="gap-0 overflow-hidden py-0 shadow-none">
    <form class="space-y-4 p-4" @submit.prevent="apply">
      <div class="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <div class="space-y-1.5">
          <Label>بازه زمانی</Label>
          <Select v-model="draft.preset">
            <SelectTrigger class="w-full"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem v-for="(label, key) in PRESET_LABELS" :key="key" :value="key">{{ label }}</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <template v-if="draft.preset === 'custom'">
          <div class="space-y-1.5">
            <Label>از تاریخ</Label>
            <JalaliDateInput v-model="draft.date_from" :invalid="!!rangeError" />
          </div>
          <div class="space-y-1.5">
            <Label>تا تاریخ</Label>
            <JalaliDateInput v-model="draft.date_to" :invalid="!!rangeError" />
          </div>
        </template>

        <div class="space-y-1.5">
          <Label>سال شمسی</Label>
          <Select v-model="draft.year">
            <SelectTrigger class="w-full"><SelectValue placeholder="همه سال‌ها" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="all">همه سال‌ها</SelectItem>
              <SelectItem v-for="y in store.options.years" :key="y" :value="String(y)">{{ faNum(y).replace(/٬/g, '') }}</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div class="space-y-1.5">
          <Label>ماه شمسی</Label>
          <Select v-model="draft.month">
            <SelectTrigger class="w-full"><SelectValue placeholder="همه ماه‌ها" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="all">همه ماه‌ها</SelectItem>
              <SelectItem v-for="(m, i) in JALALI_MONTHS" :key="m" :value="String(i + 1)">{{ m }}</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div class="space-y-1.5">
          <Label>مشتری (بانک مشتریان)</Label>
          <CrmCustomerPicker v-model="draft.customer" placeholder="همه مشتریان" />
        </div>
        <div class="space-y-1.5">
          <Label>گرید</Label>
          <Select v-model="draft.product_id">
            <SelectTrigger class="w-full"><SelectValue placeholder="همه گریدها" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="all">همه گریدها</SelectItem>
              <SelectItem v-for="p in store.products" :key="p.id" :value="String(p.id)">{{ p.name }}</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div class="space-y-1.5">
          <Label>نحوه پرداخت</Label>
          <Select v-model="draft.payment_method_id">
            <SelectTrigger class="w-full"><SelectValue placeholder="همه" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="all">همه روش‌ها</SelectItem>
              <SelectItem v-for="m in store.paymentMethods" :key="m.id" :value="String(m.id)">{{ m.name }}</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div class="space-y-1.5">
          <Label>نوع فروش</Label>
          <Select v-model="draft.sale_type">
            <SelectTrigger class="w-full"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="all">همه</SelectItem>
              <SelectItem v-for="(l, k) in SALE_TYPE_LABELS" :key="k" :value="k">{{ l }}</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div class="space-y-1.5">
          <Label>نوع سند</Label>
          <Select v-model="draft.document_type">
            <SelectTrigger class="w-full"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="all">همه</SelectItem>
              <SelectItem v-for="(l, k) in DOCUMENT_TYPE_LABELS" :key="k" :value="k">{{ l }}</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div class="space-y-1.5">
          <Label>وضعیت</Label>
          <Select v-model="draft.status">
            <SelectTrigger class="w-full"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="all">همه</SelectItem>
              <SelectItem v-for="(l, k) in SALE_STATUS_LABELS" :key="k" :value="k">{{ l }}</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div class="space-y-1.5">
          <Label>استان (از پرونده مشتری)</Label>
          <Select v-model="draft.province">
            <SelectTrigger class="w-full"><SelectValue placeholder="همه استان‌ها" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="all">همه استان‌ها</SelectItem>
              <SelectItem v-for="p in store.options.provinces" :key="p" :value="p">{{ p }}</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div class="space-y-1.5">
          <Label>صنعت (از پرونده مشتری)</Label>
          <Select v-model="draft.industry">
            <SelectTrigger class="w-full"><SelectValue placeholder="همه صنعت‌ها" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="all">همه صنعت‌ها</SelectItem>
              <SelectItem v-for="i in store.options.industries" :key="i" :value="i">{{ i }}</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div v-if="showSearch" class="space-y-1.5 sm:col-span-2">
          <Label>جستجو</Label>
          <div class="relative">
            <Icon name="lucide:search" class="absolute right-3 top-2.5 size-4 text-muted-foreground" />
            <Input v-model="draft.search" dir="rtl" class="w-full pr-9 text-right" placeholder="نام مشتری، گرید یا توضیحات..." />
          </div>
        </div>
      </div>

      <p v-if="rangeError" class="text-sm text-destructive" role="alert">{{ rangeError }}</p>

      <div class="flex flex-wrap items-center gap-2">
        <Button type="submit" class="gap-2">
          <Icon name="lucide:filter" class="size-4" /> اعمال فیلترها
        </Button>
        <Button type="button" variant="ghost" @click="reset">بازنشانی</Button>
        <span v-if="store.activeFilterCount" class="text-xs text-muted-foreground">
          {{ faNum(store.activeFilterCount) }} فیلتر فعال
        </span>
      </div>
    </form>
  </Card>
</template>

<script setup lang="ts">
import { JALALI_MONTHS } from '~/utils/jalali'
import { DOCUMENT_TYPE_LABELS, PRESET_LABELS, SALE_STATUS_LABELS, SALE_TYPE_LABELS, faNum } from '~/utils/crm'
import type { CrmFilters } from '~/stores/crm'

defineProps<{ showSearch?: boolean }>()
const emit = defineEmits<{ apply: [] }>()

const store = useCrmStore()
const draft = reactive<CrmFilters>({ ...store.filters })
const rangeError = ref('')

// Keep the staged copy in step when the store changes from outside (deep link, reset).
watch(() => ({ ...store.filters }), (v) => { Object.assign(draft, v) }, { deep: true })

function apply() {
  const prev = { ...store.filters }
  Object.assign(store.filters, draft)
  const problem = store.validateFilters()
  if (problem) {
    Object.assign(store.filters, prev) // an invalid range never reaches the table or the charts
    rangeError.value = problem
    return
  }
  rangeError.value = ''
  store.page = 1
  emit('apply')
}
function reset() {
  store.resetFilters()
  rangeError.value = ''
  emit('apply')
}
</script>
