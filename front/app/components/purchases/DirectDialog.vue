<!-- <PurchasesDirectDialog v-model:open :edit="row|null" @saved /> : register / edit a DIRECT purchase
     (no request, no quotations). The document number is typed by the expert. -->
<template>
  <Dialog :open="open" @update:open="emit('update:open', $event)">
    <DialogContent class="max-h-[90vh] max-w-2xl overflow-y-auto" dir="rtl">
      <DialogHeader><DialogTitle>{{ edit ? 'ویرایش خرید مستقیم' : 'ثبت خرید مستقیم' }}</DialogTitle></DialogHeader>
      <div class="grid gap-4 sm:grid-cols-2">
        <PurchasesField label="شمارهٔ خرید یا شمارهٔ سند" required :error="errs.doc_no"><Input v-model="form.doc_no" dir="ltr" class="text-right" autocomplete="off" /></PurchasesField>
        <PurchasesField label="تاریخ خرید" required :error="errs.purchase_date"><JalaliDateInput v-model="form.purchase_date" /></PurchasesField>
        <PurchasesField label="شرح و نام کالا یا خدمت" required :error="errs.title" class="sm:col-span-2"><Input v-model="form.title" /></PurchasesField>
        <PurchasesField label="تأمین‌کننده" required :error="errs.supplier_id || errs.supplier_name" hint="از بانک تأمین‌کنندگان انتخاب کنید؛ برای فروشندهٔ ثبت‌نشده، نام او را بنویسید" class="relative">
          <Input v-model="form.supplier_name" placeholder="جستجو یا نوشتن نام…" @input="searchSup" @focus="searchSup" @blur="closeSup" />
          <ul v-if="options.length" class="absolute z-30 mt-1 max-h-48 w-full overflow-auto rounded-md border bg-background shadow">
            <li v-for="o in options" :key="o.id" class="cursor-pointer px-3 py-2 text-sm hover:bg-muted" @mousedown.prevent="pick(o)">{{ o.name }}</li>
          </ul>
          <p v-if="form.supplier_id" class="mt-1 text-xs text-emerald-700">از بانک تأمین‌کنندگان انتخاب شد</p>
        </PurchasesField>
        <PurchasesField label="مبلغ خرید (ریال)" required :error="errs.amount"><PurchasesMoney v-model="form.amount" rial /></PurchasesField>
        <PurchasesField label="محل مصرف" required :error="errs.usage_place"><Input v-model="form.usage_place" /></PurchasesField>
        <PurchasesField label="گروه کالایی (اختیاری)" hint="برای نمایش در تحلیل گروه‌های کالایی">
          <select v-model="form.category_id" class="h-9 w-full rounded-md border border-input bg-transparent px-3 text-sm">
            <option value="">بدون گروه</option>
            <option v-for="c in store.meta?.categories" :key="c.id" :value="String(c.id)">{{ c.name }}</option>
          </select>
        </PurchasesField>
        <PurchasesField label="توضیحات (اختیاری)" class="sm:col-span-2"><Textarea v-model="form.description" rows="2" /></PurchasesField>
      </div>
      <p v-if="formError" class="text-sm text-destructive">{{ formError }}</p>
      <DialogFooter><Button variant="outline" @click="emit('update:open', false)">انصراف</Button><Button :disabled="busy" @click="save">ثبت</Button></DialogFooter>
    </DialogContent>
  </Dialog>
</template>

<script setup lang="ts">
import { ApiError } from '~/services/backendApi'
import { fieldErrors } from '~/utils/purchase'
import type { DirectPurchase } from '~/utils/purchase'

const props = defineProps<{ open: boolean, edit: DirectPurchase | null }>()
const emit = defineEmits<{ (e: 'update:open', v: boolean): void, (e: 'saved'): void }>()
const store = usePurchasesStore()
const notify = useNotify()
const form = reactive<{ doc_no: string, purchase_date: string, title: string, supplier_id: number | null, supplier_name: string, amount: number | null, usage_place: string, category_id: string, description: string }>(
  { doc_no: '', purchase_date: '', title: '', supplier_id: null, supplier_name: '', amount: null, usage_place: '', category_id: '', description: '' })
const errs = ref<Record<string, string>>({})
const formError = ref('')
const busy = ref(false)
const options = ref<{ id: number, name: string }[]>([])

watch(() => props.open, (o) => {
  if (!o) return
  const d = props.edit
  Object.assign(form, { doc_no: d?.doc_no ?? '', purchase_date: d?.purchase_date ?? '', title: d?.title ?? '', supplier_id: d?.supplier_id ?? null, supplier_name: d?.supplier_name ?? '',
    amount: d?.amount ?? null, usage_place: d?.usage_place ?? '', category_id: d?.category_id ? String(d.category_id) : '', description: d?.description ?? '' })
  errs.value = {}
  formError.value = ''
  options.value = []
})

let timer: ReturnType<typeof setTimeout> | undefined
function searchSup() {
  form.supplier_id = null // typing again: the earlier pick no longer applies
  clearTimeout(timer)
  timer = setTimeout(async () => { try { options.value = await store.searchSuppliers(form.supplier_name) } catch { options.value = [] } }, 250)
}
function pick(o: { id: number, name: string }) { form.supplier_id = o.id; form.supplier_name = o.name; options.value = [] }
function closeSup() { setTimeout(() => { options.value = [] }, 120) }

async function save() {
  busy.value = true
  errs.value = {}
  formError.value = ''
  try {
    await store.saveDirect({
      doc_no: form.doc_no, purchase_date: form.purchase_date || null, title: form.title, supplier_id: form.supplier_id, supplier_name: form.supplier_id ? null : form.supplier_name,
      amount: form.amount, usage_place: form.usage_place, category_id: form.category_id ? Number(form.category_id) : null, description: form.description,
    }, props.edit?.id)
    notify.success(props.edit ? 'خرید مستقیم ویرایش شد' : 'خرید مستقیم ثبت شد')
    emit('saved')
    emit('update:open', false)
  }
  catch (e) {
    errs.value = e instanceof ApiError ? fieldErrors(e.details) : {}
    formError.value = e instanceof ApiError ? e.message : 'ثبت انجام نشد.'
  }
  finally { busy.value = false }
}
</script>
