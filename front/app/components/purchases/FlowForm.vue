<!-- <PurchasesFlowForm :edit="request?" @saved="r => ..." /> : the purchase-request wizard of the warehouse.
     Part 1 = general info (request number, auto date, unit, requester, need date); part 2 = the goods lines,
     each with its OWN stock, reorder point, request type, subject and priority. -->
<template>
  <div class="space-y-6">
    <section class="space-y-4 rounded-xl border p-5">
      <h2 class="flex items-center gap-2 text-base font-semibold"><span class="flex size-6 items-center justify-center rounded-full bg-primary text-xs text-primary-foreground">۱</span>اطلاعات کلی درخواست</h2>
      <div class="grid gap-4 md:grid-cols-3">
        <PurchasesField label="شماره درخواست" required :error="errs.request_no"><Input v-model="head.request_no" dir="ltr" class="text-right" maxlength="30" /></PurchasesField>
        <PurchasesField label="تاریخ ثبت" hint="به‌صورت خودکار ثبت می‌شود"><Input :model-value="todayJalali" disabled /></PurchasesField>
        <PurchasesField label="واحد متقاضی" required :error="errs.requester_unit">
          <select v-model="head.requester_unit" class="h-9 w-full rounded-md border border-input bg-transparent px-3 text-sm">
            <option value="">انتخاب کنید…</option>
            <option v-for="u in unitOptions" :key="u" :value="u">{{ u }}</option>
          </select>
        </PurchasesField>
        <PurchasesField label="نام درخواست‌کننده" required :error="errs.requester_name"><Input v-model="head.requester_name" /></PurchasesField>
        <PurchasesField label="تاریخ نیاز" required :error="errs.required_date"><JalaliDateInput v-model="head.required_date" /></PurchasesField>
      </div>
    </section>

    <section class="space-y-4 rounded-xl border p-5">
      <div class="flex items-center justify-between">
        <h2 class="flex items-center gap-2 text-base font-semibold"><span class="flex size-6 items-center justify-center rounded-full bg-primary text-xs text-primary-foreground">۲</span>اقلام درخواستی</h2>
        <Button type="button" variant="outline" size="sm" class="gap-2" @click="addLine"><Icon name="lucide:plus" class="size-4" />افزودن کالا</Button>
      </div>
      <p v-if="errs.items" class="text-sm text-destructive">{{ errs.items }}</p>

      <div v-for="(l, i) in lines" :key="l.key" class="space-y-4 rounded-lg border bg-muted/20 p-4">
        <div class="flex items-center justify-between">
          <b class="text-sm">کالای {{ i + 1 }}</b>
          <button v-if="lines.length > 1 && !l.locked" type="button" class="text-xs text-destructive" @click="lines.splice(i, 1)">حذف کالا</button>
        </div>
        <div class="grid gap-4 md:grid-cols-3">
          <PurchasesField label="نام کالا" required :error="errs[`items.${i}.product_id`]">
            <PurchasesProductPicker :name="l.name" :disabled="l.locked" @pick="p => pick(l, p)" />
          </PurchasesField>
          <PurchasesField label="شمارهٔ کالا" hint="خودکار از اطلاعات کالا"><Input :model-value="l.product_code ?? ''" dir="ltr" class="text-right" disabled /></PurchasesField>
          <PurchasesField label="گروه کالایی" required :error="errs[`items.${i}.category_id`]" :hint="l.categoryFromProduct ? 'خودکار از کالا' : 'برای این کالا گروهی ثبت نشده؛ انتخاب کنید'">
            <select v-model="l.category_id" :disabled="l.categoryFromProduct || l.locked" class="h-9 w-full rounded-md border border-input bg-transparent px-3 text-sm disabled:opacity-60">
              <option :value="null">انتخاب کنید…</option>
              <option v-for="c in meta?.categories" :key="c.id" :value="c.id">{{ c.name }}</option>
            </select>
          </PurchasesField>
          <PurchasesField label="واحد اندازه‌گیری" required :error="errs[`items.${i}.unit`]" :hint="l.unitFromProduct ? 'خودکار از کالا' : undefined">
            <Input v-model="l.unit" :disabled="l.unitFromProduct || l.locked" />
          </PurchasesField>
          <PurchasesField label="مقدار درخواستی" required :error="errs[`items.${i}.quantity`]"><PurchasesMoney v-model="l.quantity" :disabled="l.locked" :decimals="3" /></PurchasesField>
          <PurchasesField label="موجودی فعلی انبار" required :error="errs[`items.${i}.current_stock`]" hint="فعلاً دستی ثبت می‌شود"><PurchasesMoney v-model="l.current_stock" :disabled="l.locked" :decimals="3" /></PurchasesField>
          <PurchasesField label="نقطه سفارش" hint="اختیاری" :error="errs[`items.${i}.reorder_point`]"><PurchasesMoney v-model="l.reorder_point" :disabled="l.locked" :decimals="3" /></PurchasesField>
          <PurchasesField label="نوع درخواست" required :error="errs[`items.${i}.request_type`]">
            <select v-model="l.request_type" :disabled="l.locked" class="h-9 w-full rounded-md border border-input bg-transparent px-3 text-sm">
              <option value="">انتخاب کنید…</option>
              <option v-for="t in typeOptions(l)" :key="t" :value="t">{{ t }}</option>
            </select>
          </PurchasesField>
          <PurchasesField label="موضوع خرید" required :error="errs[`items.${i}.purchase_subject`]">
            <select v-model="l.purchase_subject" :disabled="l.locked" class="h-9 w-full rounded-md border border-input bg-transparent px-3 text-sm">
              <option value="">انتخاب کنید…</option>
              <option v-for="s in meta?.subjects" :key="s.value" :value="s.value">{{ s.label }}</option>
            </select>
          </PurchasesField>
          <PurchasesField label="اولویت خرید" required :error="errs[`items.${i}.priority`]">
            <select v-model="l.priority" :disabled="l.locked" class="h-9 w-full rounded-md border border-input bg-transparent px-3 text-sm">
              <option value="">انتخاب کنید…</option>
              <option v-for="p in meta?.priorities" :key="p.value" :value="p.value">{{ p.label }}</option>
            </select>
          </PurchasesField>
        </div>
      </div>
    </section>

    <p v-if="formError" class="rounded-lg border border-destructive/40 bg-destructive/5 p-3 text-sm text-destructive">{{ formError }}</p>
    <div class="flex justify-end gap-2">
      <Button type="button" :disabled="busy" class="gap-2" @click="save"><Icon name="lucide:send" class="size-4" />{{ edit ? 'ثبت اصلاحات و ارسال مجدد' : 'ثبت نهایی و ارجاع به تدارکات' }}</Button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ApiError } from '~/services/backendApi'
import type { CatalogProduct } from '~/utils/purchase'
import type { FlowItem, FlowRequest } from '~/utils/purchaseFlow'

interface Line {
  key: number, id?: number, name: string, product_id: number | null, product_code: string | null, category_id: number | null,
  categoryFromProduct: boolean, unit: string, unitFromProduct: boolean, quantity: number | null, current_stock: number | null,
  reorder_point: number | null, request_type: string, purchase_subject: string, priority: string, locked: boolean,
}
const props = defineProps<{ edit?: FlowRequest | null }>()
const emit = defineEmits<{ (e: 'saved', r: FlowRequest): void }>()
const store = usePurchaseFlowStore()
const notify = useNotify()
const meta = computed(() => store.meta)
await store.loadMeta()

const head = reactive({ request_no: props.edit?.request_no ?? '', requester_unit: props.edit?.requester_unit ?? '', requester_name: props.edit?.requester_name ?? '', required_date: props.edit?.required_date ?? '' })
const todayJalali = new Intl.DateTimeFormat('fa-IR-u-ca-persian', { year: 'numeric', month: '2-digit', day: '2-digit' }).format(new Date())
const unitOptions = computed(() => [...new Set([...(head.requester_unit ? [head.requester_unit] : []), ...(meta.value?.units ?? [])])])
const typeOptions = (l: Line) => [...new Set([...(l.request_type ? [l.request_type] : []), ...(meta.value?.request_types ?? [])])]

let seq = 0
const blank = (): Line => ({ key: ++seq, name: '', product_id: null, product_code: null, category_id: null, categoryFromProduct: false, unit: '', unitFromProduct: false, quantity: null, current_stock: null, reorder_point: null, request_type: '', purchase_subject: '', priority: '', locked: false })
const fromItem = (i: FlowItem): Line => ({
  ...blank(), id: i.id, name: i.name, product_id: i.product_id, product_code: i.product_code, category_id: i.category_id, categoryFromProduct: true,
  unit: i.unit, unitFromProduct: true, quantity: i.quantity, current_stock: i.current_stock, reorder_point: i.reorder_point,
  request_type: i.request_type ?? '', purchase_subject: i.purchase_subject ?? '', priority: i.priority ?? '',
  locked: i.status === 'CANCELLED' || ['IN_FINANCE', 'PAID', 'SHIPPING', 'DELIVERED'].includes(i.status),
})
const lines = reactive<Line[]>(props.edit?.items.length ? props.edit.items.map(fromItem) : [blank()])
const addLine = () => lines.push(blank())

function pick(l: Line, p: CatalogProduct | null) {
  if (!p) return
  Object.assign(l, {
    product_id: p.id, name: p.name, product_code: p.code, category_id: p.category_id ?? null, categoryFromProduct: !!p.category_id,
    unit: p.unit || '', unitFromProduct: !!p.unit,
  })
}

const errs = ref<Record<string, string>>({})
const formError = ref('')
const busy = ref(false)
async function save() {
  busy.value = true
  errs.value = {}
  formError.value = ''
  const body = {
    ...head,
    items: lines.map(l => ({
      id: l.id, product_id: l.product_id, category_id: l.categoryFromProduct ? undefined : l.category_id, unit: l.unitFromProduct ? undefined : l.unit,
      quantity: l.quantity, current_stock: l.current_stock, reorder_point: l.reorder_point, request_type: l.request_type || null,
      purchase_subject: l.purchase_subject || null, priority: l.priority || null,
    })),
  }
  try {
    const r = props.edit ? await store.update(props.edit.id, body) : await store.create(body)
    notify.success(props.edit ? 'اصلاحات ثبت و درخواست دوباره ارسال شد' : 'درخواست ثبت و به تدارکات ارجاع شد')
    emit('saved', r)
  }
  catch (e) {
    errs.value = e instanceof ApiError ? fieldErrors(e.details) : {}
    formError.value = e instanceof ApiError ? e.message : 'ثبت انجام نشد.'
  }
  finally { busy.value = false }
}
</script>
