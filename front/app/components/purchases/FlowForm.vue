<!-- <PurchasesFlowForm :edit="request?" @saved="r => ..." /> : the purchase-request form of the warehouse.
     Part 1 = request info (number, auto date, unit, requester, need date); part 2 = the goods lines, each with its OWN
     stock, reorder point, request type, subject and priority. Fields the catalog already fills (code, group, unit)
     are shown as a note / disabled instead of as separate inputs. Same payload as before. -->
<template>
  <div class="space-y-6">
    <section class="space-y-4 rounded-xl border p-5">
      <div class="flex flex-wrap items-baseline justify-between gap-2">
        <h2 class="text-base font-semibold">اطلاعات درخواست</h2>
        <span class="text-xs text-muted-foreground">تاریخ ثبت: {{ todayJalali }} (خودکار)</span>
      </div>
      <div class="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <PurchasesField label="شماره درخواست" required :error="errs.request_no"><Input v-model="head.request_no" dir="ltr" class="text-right" maxlength="30" /></PurchasesField>
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

    <section class="space-y-4">
      <div class="flex items-baseline justify-between gap-2">
        <h2 class="text-base font-semibold">اقلام درخواستی</h2>
        <span class="text-xs text-muted-foreground">{{ lines.length.toLocaleString('fa-IR') }} کالا</span>
      </div>
      <p v-if="errs.items" class="text-sm text-destructive">{{ errs.items }}</p>

      <div v-for="(l, i) in lines" :key="l.key" class="space-y-4 rounded-xl border p-4">
        <div class="flex items-center justify-between">
          <b class="text-sm">کالای {{ (i + 1).toLocaleString('fa-IR') }}</b>
          <button v-if="lines.length > 1 && !l.locked" type="button" class="text-xs text-destructive hover:underline" @click="lines.splice(i, 1)">حذف این کالا</button>
          <span v-else-if="l.locked" class="text-xs text-muted-foreground">در مسیر پرداخت یا تحویل است؛ قابل ویرایش نیست</span>
        </div>

        <!-- what and how much -->
        <div class="grid gap-4 md:grid-cols-4">
          <PurchasesField class="md:col-span-2" label="نام کالا" required :error="errs[`items.${i}.product_id`]">
            <PurchasesProductPicker :name="l.name" :disabled="l.locked" @pick="p => pick(l, p)" />
          </PurchasesField>
          <PurchasesField label="مقدار درخواستی" required :error="errs[`items.${i}.quantity`]"><PurchasesMoney v-model="l.quantity" :disabled="l.locked" :decimals="3" /></PurchasesField>
          <PurchasesField label="واحد" required :error="errs[`items.${i}.unit`]"><Input v-model="l.unit" :disabled="l.unitFromProduct || l.locked" /></PurchasesField>
        </div>
        <p v-if="l.product_id" class="-mt-2 text-xs text-muted-foreground">
          <span v-if="l.product_code" dir="ltr">کد {{ l.product_code }}</span><span v-if="l.product_code && l.categoryFromProduct"> · </span><span v-if="l.categoryFromProduct">گروه: {{ categoryName(l.category_id) }}</span>
        </p>

        <!-- why and how urgent -->
        <div class="grid gap-4 md:grid-cols-3">
          <PurchasesField label="اولویت خرید" required :error="errs[`items.${i}.priority`]">
            <select v-model="l.priority" :disabled="l.locked" class="h-9 w-full rounded-md border border-input bg-transparent px-3 text-sm">
              <option value="">انتخاب کنید…</option>
              <option v-for="p in meta?.priorities" :key="p.value" :value="p.value">{{ p.label }}</option>
            </select>
          </PurchasesField>
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
        </div>

        <!-- stock + the category only when the catalog has none for this product -->
        <div class="grid gap-4 md:grid-cols-3">
          <PurchasesField label="موجودی فعلی انبار" required :error="errs[`items.${i}.current_stock`]" hint="فعلاً دستی ثبت می‌شود"><PurchasesMoney v-model="l.current_stock" :disabled="l.locked" :decimals="3" /></PurchasesField>
          <PurchasesField label="نقطه سفارش" hint="اختیاری" :error="errs[`items.${i}.reorder_point`]"><PurchasesMoney v-model="l.reorder_point" :disabled="l.locked" :decimals="3" /></PurchasesField>
          <PurchasesField v-if="!l.categoryFromProduct" label="گروه کالایی" required :error="errs[`items.${i}.category_id`]" hint="برای این کالا گروهی ثبت نشده است">
            <select v-model="l.category_id" :disabled="l.locked" class="h-9 w-full rounded-md border border-input bg-transparent px-3 text-sm disabled:opacity-60">
              <option :value="null">انتخاب کنید…</option>
              <option v-for="c in meta?.categories" :key="c.id" :value="c.id">{{ c.name }}</option>
            </select>
          </PurchasesField>
        </div>
      </div>

      <button type="button" class="w-full rounded-xl border border-dashed py-3 text-sm text-muted-foreground transition-colors hover:bg-muted/40 hover:text-foreground" @click="addLine">+ افزودن کالای دیگر</button>
    </section>

    <p v-if="formError" id="flow-form-error" role="alert" class="rounded-lg border border-destructive/40 bg-destructive/5 p-3 text-sm text-destructive">{{ formError }}</p>

    <!-- the submit button stays in reach however long the list is -->
    <div class="sticky bottom-0 z-10 -mx-1 flex items-center justify-between gap-3 border-t bg-background/95 px-1 py-3 backdrop-blur">
      <span class="text-xs text-muted-foreground">{{ edit ? 'پس از ثبت، درخواست دوباره برای تدارکات ارسال می‌شود.' : 'پس از ثبت، درخواست برای تدارکات ارسال می‌شود.' }}</span>
      <Button type="button" :disabled="busy" @click="save">{{ busy ? 'در حال ثبت…' : edit ? 'ثبت اصلاحات و ارسال مجدد' : 'ثبت درخواست' }}</Button>
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
const categoryName = (id: number | null) => meta.value?.categories.find(c => c.id === id)?.name ?? '—'

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
  finally {
    busy.value = false
    if (formError.value) nextTick(() => document.getElementById('flow-form-error')?.scrollIntoView({ block: 'center', behavior: 'smooth' }))
  }
}
</script>
