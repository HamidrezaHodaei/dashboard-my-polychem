<!-- <RequestSampleFormWizard v-model:open :request-id /> : six-step wizard (create / edit a request).
     Step 1 customer · 2 products · 3 sample requirements · 4 application & technical · 5 shipping ·
     6 review. «ذخیره پیش‌نویس» keeps it as DRAFT; «ثبت درخواست» submits it to the approval workflow
     (submitting is NOT approval). -->
<template>
  <Dialog :open="open" @update:open="v => emit('update:open', v)">
    <DialogContent
      dir="rtl"
      class="customer-wizard flex max-h-[94vh] flex-col gap-0 overflow-hidden p-0 sm:max-w-3xl [&_input:not([dir=ltr])]:text-right [&_textarea:not([dir=ltr])]:text-right"
      @interact-outside.prevent
    >
      <DialogHeader class="border-b px-4 py-4 text-right sm:px-6">
        <DialogTitle class="text-lg font-semibold">
          {{ requestId ? 'ویرایش درخواست نمونه' : 'درخواست نمونه محصول جدید' }}
        </DialogTitle>
        <DialogDescription class="sr-only">
          ویزارد شش‌مرحله‌ای ثبت درخواست نمونه محصول.
        </DialogDescription>
      </DialogHeader>

      <!-- step indicator -->
      <div class="px-4 pb-2 pt-5 sm:px-6">
        <ol class="-mx-1 flex w-max min-w-full items-center gap-2 overflow-x-auto px-1 py-1" aria-label="مراحل ثبت درخواست">
          <template v-for="(s, i) in STEPS" :key="s.key">
            <li class="flex shrink-0 items-center" :aria-current="i === step ? 'step' : undefined">
              <button
                type="button"
                class="flex items-center gap-2 rounded-full focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                :disabled="i > furthest"
                :title="s.title"
                @click="goTo(i)"
              >
                <span
                  class="grid size-8 shrink-0 place-items-center rounded-full text-sm font-semibold transition-colors sm:size-9"
                  :class="i <= step ? 'bg-primary text-primary-foreground' : i <= furthest ? 'bg-primary/15 text-primary' : 'bg-muted text-muted-foreground'"
                >
                  <Icon v-if="i < step" name="lucide:check" class="size-4" />
                  <template v-else>{{ i + 1 }}</template>
                </span>
                <span v-if="i === step" class="hidden whitespace-nowrap pe-1 text-sm font-medium text-primary sm:inline">{{ s.title }}</span>
              </button>
            </li>
            <li v-if="i < STEPS.length - 1" class="h-0.5 min-w-4 flex-1 rounded-full transition-colors" :class="i < step ? 'bg-primary' : 'bg-border'" aria-hidden="true" />
          </template>
        </ol>
        <p class="mt-2 text-xs text-muted-foreground sm:hidden">مرحله {{ step + 1 }} از {{ STEPS.length }}: {{ STEPS[step]!.title }}</p>
      </div>

      <div v-if="loadingExisting" class="p-10 text-center text-sm text-muted-foreground">
        در حال بارگذاری...
      </div>
      <div v-else ref="bodyEl" class="flex-1 space-y-5 overflow-y-auto px-4 py-4 sm:px-6">
        <!-- ───────── 1. customer ───────── -->
        <section v-show="step === 0" class="space-y-4">
          <div class="space-y-1.5">
            <Label class="font-semibold">مشتری <span class="text-destructive">*</span></Label>
            <CrmCustomerPicker :model-value="customer" :disabled="!!requestId && lockedCustomer" @update:model-value="onCustomer" />
            <p v-if="err.customer_id" class="text-xs text-destructive">{{ err.customer_id }}</p>
          </div>

          <div v-if="customerInfo" class="space-y-2 rounded-xl border bg-muted/20 p-4 text-sm">
            <div class="grid gap-x-6 gap-y-2 sm:grid-cols-2">
              <p><span class="text-muted-foreground">نام: </span><b dir="auto">{{ customerInfo.name }}</b></p>
              <p v-if="customerInfo.company_name"><span class="text-muted-foreground">نام شرکت: </span>{{ customerInfo.company_name }}</p>
              <p v-if="customerInfo.brand"><span class="text-muted-foreground">برند: </span>{{ customerInfo.brand }}</p>
              <p v-if="customerInfo.company_phone"><span class="text-muted-foreground">تلفن شرکت: </span><span dir="ltr">{{ customerInfo.company_phone }}</span></p>
              <p v-if="customerInfo.province || customerInfo.city"><span class="text-muted-foreground">محل: </span>{{ [customerInfo.province, customerInfo.city].filter(Boolean).join('، ') }}</p>
            </div>
            <div v-if="customerInfo.contacts?.length" class="border-t pt-2">
              <p class="mb-1 text-xs font-medium text-muted-foreground">اشخاص رابط</p>
              <ul class="space-y-1">
                <li v-for="(c, i) in customerInfo.contacts" :key="i" class="flex flex-wrap items-center gap-x-3">
                  <span class="font-medium">{{ c.name || '—' }}</span>
                  <span v-if="c.position" class="text-xs text-muted-foreground">{{ c.position }}</span>
                  <span v-if="c.mobile || c.landline" dir="ltr" class="text-xs">{{ c.mobile || c.landline }}</span>
                </li>
              </ul>
            </div>
          </div>

          <div class="grid gap-4 sm:grid-cols-2">
            <div class="space-y-1.5">
              <Label class="font-semibold">شمارهٔ حوالهٔ نمونه محصول <span class="text-destructive">*</span></Label>
              <Input v-model="form.dispatch_ref_number" dir="ltr" maxlength="100" placeholder="مثلاً SMP-1405-0123" :aria-invalid="!!err.dispatch_ref_number" />
              <p v-if="err.dispatch_ref_number" class="text-xs text-destructive">{{ err.dispatch_ref_number }}</p>
            </div>
            <div class="space-y-1.5">
              <Label class="font-semibold">اولویت</Label>
              <Select v-model="form.priority">
                <SelectTrigger class="w-full"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem v-for="(m, k) in PRIORITY_META" :key="k" :value="k">{{ m.label }}</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div class="space-y-1.5 sm:col-span-2">
              <Label class="font-semibold">کارشناس فروش مسئول</Label>
              <Select v-model="repModel">
                <SelectTrigger class="w-full"><SelectValue placeholder="خودم" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="me">خودم</SelectItem>
                  <SelectItem v-for="r in reps" :key="r.id" :value="String(r.id)">{{ r.name }}</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </section>

        <!-- ───────── 2. products ───────── -->
        <section v-show="step === 1" class="space-y-4">
          <p class="text-xs text-muted-foreground">هر محصول یک ردیف مستقل است؛ نام محصول و گرید از فهرست‌های بانک اطلاعات مشتریان انتخاب می‌شود.</p>
          <p v-if="err.items" class="text-sm text-destructive">{{ err.items }}</p>
          <div v-for="(it, i) in form.items" :key="i" class="space-y-3 rounded-xl border p-4">
            <div class="flex items-center justify-between">
              <h3 class="text-sm font-semibold">محصول {{ toPersianDigits(i + 1) }}</h3>
              <Button type="button" variant="ghost" size="icon" class="text-destructive hover:text-destructive" title="حذف این محصول" aria-label="حذف این محصول" :disabled="form.items.length === 1" @click="removeItem(i)">
                <Icon name="lucide:trash-2" class="size-4" />
              </Button>
            </div>
            <div class="grid gap-3 sm:grid-cols-2">
              <div class="space-y-1.5">
                <Label>گروه محصول</Label>
                <Input v-model="it.product_category" dir="auto" maxlength="200" placeholder="مثلاً پلی‌اتیلن" />
              </div>
              <div class="space-y-1.5">
                <Label>نام محصول <span class="text-destructive">*</span></Label>
                <CustomerOptionSelect v-model="it.product_name" kind="CONSUMED" placeholder="انتخاب محصول" :invalid="!!err[`items.${i}.product_name`]" />
                <p v-if="err[`items.${i}.product_name`]" class="text-xs text-destructive">{{ err[`items.${i}.product_name`] }}</p>
              </div>
              <div class="space-y-1.5">
                <Label>گرید</Label>
                <CustomerOptionSelect v-model="it.grade" kind="GRADE" placeholder="انتخاب گرید" />
              </div>
              <div class="space-y-1.5">
                <Label>محصول جایگزین پیشنهادی</Label>
                <CustomerOptionSelect v-model="it.alternative_product" kind="CONSUMED" placeholder="اختیاری" />
              </div>
              <div class="space-y-1.5 sm:col-span-2">
                <Label>مشخصات فنی محصول</Label>
                <Textarea v-model="it.specifications" rows="2" dir="auto" placeholder="MFI، چگالی، کاربرد گرید و..." />
              </div>
            </div>
          </div>
          <Button type="button" variant="outline" class="gap-2" @click="addItem">
            <Icon name="lucide:plus" class="size-4" /> افزودن محصول
          </Button>
        </section>

        <!-- ───────── 3. sample requirements ───────── -->
        <section v-show="step === 2" class="space-y-4">
          <div v-for="(it, i) in form.items" :key="`q${i}`" class="space-y-3 rounded-xl border p-4">
            <h3 class="text-sm font-semibold" dir="auto">{{ it.product_name || `محصول ${toPersianDigits(i + 1)}` }}<span v-if="it.grade" class="font-normal text-muted-foreground"> · {{ it.grade }}</span></h3>
            <div class="grid gap-3 sm:grid-cols-4">
              <div class="space-y-1.5">
                <Label>مقدار نمونه <span class="text-destructive">*</span></Label>
                <Input v-model="it.quantity" dir="ltr" inputmode="decimal" class="text-right" :aria-invalid="!!err[`items.${i}.quantity`]" />
                <p v-if="err[`items.${i}.quantity`]" class="text-xs text-destructive">{{ err[`items.${i}.quantity`] }}</p>
              </div>
              <div class="space-y-1.5">
                <Label>واحد</Label>
                <Select v-model="it.unit">
                  <SelectTrigger class="w-full"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem v-for="u in UNIT_OPTIONS" :key="u.value" :value="u.value">{{ u.label }}</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div class="space-y-1.5">
                <Label>تعداد نمونه / بسته</Label>
                <Input v-model="it.number_of_samples" dir="ltr" inputmode="numeric" class="text-right" :aria-invalid="!!err[`items.${i}.number_of_samples`]" />
                <p v-if="err[`items.${i}.number_of_samples`]" class="text-xs text-destructive">{{ err[`items.${i}.number_of_samples`] }}</p>
              </div>
              <div class="space-y-1.5">
                <Label>بسته‌بندی نمونه</Label>
                <Input v-model="it.packaging" dir="auto" maxlength="200" placeholder="کیسهٔ ۱ کیلویی" />
              </div>
            </div>
          </div>
          <div class="grid gap-4 sm:grid-cols-2">
            <div class="space-y-1.5">
              <Label>تاریخ موردنیاز دریافت نمونه</Label>
              <JalaliDateInput v-model="form.required_delivery_date" :min="todayIso()" :invalid="!!err.required_delivery_date" />
              <p v-if="err.required_delivery_date" class="text-xs text-destructive">{{ err.required_delivery_date }}</p>
            </div>
            <div class="space-y-1.5">
              <Label>هدف دریافت نمونه</Label>
              <Textarea v-model="form.purpose" rows="2" dir="auto" placeholder="ارزیابی کیفیت، آزمایش تولید، مقایسه با رقیب..." />
            </div>
            <div class="space-y-1.5 sm:col-span-2">
              <Label>الزامات و توضیحات فنی مشتری</Label>
              <Textarea v-model="form.technical_requirements" rows="3" dir="auto" />
            </div>
          </div>
        </section>

        <!-- ───────── 4. application & technical ───────── -->
        <section v-show="step === 3" class="space-y-4">
          <div class="grid gap-4 sm:grid-cols-2">
            <div class="space-y-1.5">
              <Label>کاربرد نهایی محصول</Label>
              <Input v-model="form.application" dir="auto" maxlength="255" placeholder="مثلاً لولهٔ آبرسانی" />
            </div>
            <div class="space-y-1.5">
              <Label>صنعت / حوزهٔ مصرف</Label>
              <Input v-model="form.industry" dir="auto" maxlength="255" :placeholder="customerInfo?.category || 'مثلاً بسته‌بندی'" />
            </div>
            <div class="space-y-1.5 sm:col-span-2">
              <Label>فرآیند تولید مشتری</Label>
              <Textarea v-model="form.production_process" rows="2" dir="auto" placeholder="اکسترود، تزریق، دمش..." />
            </div>
            <div class="space-y-1.5 sm:col-span-2">
              <Label>ویژگی‌های فنی موردنیاز</Label>
              <Textarea v-model="form.required_properties" rows="2" dir="auto" />
            </div>
          </div>
          <div class="space-y-2">
            <Label>مستندات فنی و نتایج آزمایش</Label>
            <div class="flex flex-wrap items-center gap-2">
              <Button type="button" variant="outline" class="gap-2" :disabled="uploading" @click="fileInput?.click()">
                <Icon :name="uploading ? 'lucide:loader-circle' : 'lucide:upload'" class="size-4" :class="uploading && 'animate-spin'" /> بارگذاری فایل
              </Button>
              <span class="text-xs text-muted-foreground">PDF، تصویر، Word، Excel، CSV — حداکثر ۱۰ مگابایت</span>
              <input ref="fileInput" type="file" class="hidden" multiple accept=".pdf,.png,.jpg,.jpeg,.webp,.doc,.docx,.xls,.xlsx,.csv,.txt" @change="onFiles">
            </div>
            <ul v-if="files.length" class="space-y-1">
              <li v-for="f in files" :key="f.id" class="flex items-center justify-between gap-2 rounded-lg border px-3 py-1.5 text-sm">
                <span class="flex min-w-0 items-center gap-2"><Icon name="lucide:paperclip" class="size-4 shrink-0 text-muted-foreground" /><span class="truncate" dir="auto">{{ f.name }}</span></span>
                <Button type="button" variant="ghost" size="icon" class="size-7 text-destructive" aria-label="حذف فایل" @click="removeFile(f.id)"><Icon name="lucide:x" class="size-4" /></Button>
              </li>
            </ul>
          </div>
        </section>

        <!-- ───────── 5. shipping ───────── -->
        <section v-show="step === 4" class="space-y-4">
          <div class="grid gap-4 sm:grid-cols-2">
            <div class="space-y-1.5">
              <Label>روش تحویل نمونه</Label>
              <Select v-model="deliveryModel">
                <SelectTrigger class="w-full"><SelectValue placeholder="انتخاب کنید" /></SelectTrigger>
                <SelectContent>
                  <SelectItem v-for="m in DELIVERY_METHODS" :key="m" :value="m">{{ m }}</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div class="space-y-1.5">
              <Label>نام تحویل‌گیرنده <span class="text-destructive">*</span></Label>
              <Input v-model="form.recipient_name" dir="auto" maxlength="200" :aria-invalid="!!err.recipient_name" />
              <p v-if="err.recipient_name" class="text-xs text-destructive">{{ err.recipient_name }}</p>
            </div>
            <div class="space-y-1.5 sm:col-span-2">
              <Label>نشانی کامل تحویل <span class="text-destructive">*</span></Label>
              <Textarea v-model="form.delivery_address" rows="2" dir="auto" :aria-invalid="!!err.delivery_address" />
              <p v-if="err.delivery_address" class="text-xs text-destructive">{{ err.delivery_address }}</p>
            </div>
            <div class="space-y-1.5">
              <Label>کشور</Label>
              <Input v-model="form.country" dir="auto" maxlength="100" placeholder="ایران" />
            </div>
            <div class="space-y-1.5">
              <Label>شهر <span class="text-destructive">*</span></Label>
              <Input v-model="form.city" dir="auto" maxlength="100" :aria-invalid="!!err.city" />
              <p v-if="err.city" class="text-xs text-destructive">{{ err.city }}</p>
            </div>
            <div class="space-y-1.5">
              <Label>کد پستی</Label>
              <Input v-model="form.postal_code" dir="ltr" inputmode="numeric" maxlength="20" class="text-right" />
            </div>
            <div class="space-y-1.5 sm:col-span-2">
              <Label>توضیحات ویژهٔ ارسال</Label>
              <Textarea v-model="form.delivery_instructions" rows="2" dir="auto" />
            </div>
          </div>
        </section>

        <!-- ───────── 6. review ───────── -->
        <section v-show="step === 5" class="space-y-4">
          <div v-for="g in summary" :key="g.title" class="rounded-xl border">
            <div class="flex items-center justify-between border-b bg-muted/30 px-4 py-2">
              <h3 class="text-sm font-semibold">{{ g.title }}</h3>
              <Button type="button" variant="ghost" size="sm" @click="goTo(g.step)">ویرایش</Button>
            </div>
            <dl class="grid gap-x-6 gap-y-2 p-4 text-sm sm:grid-cols-2">
              <div v-for="r in g.rows" :key="r.label" :class="r.wide && 'sm:col-span-2'">
                <dt class="text-xs text-muted-foreground">{{ r.label }}</dt>
                <dd class="whitespace-pre-line break-words" dir="auto">{{ r.value || '—' }}</dd>
              </div>
            </dl>
          </div>
          <div class="space-y-1.5">
            <Label>یادداشت داخلی (برای همکاران، به مشتری نمایش داده نمی‌شود)</Label>
            <Textarea v-model="form.internal_notes" rows="2" dir="auto" />
          </div>
          <p v-if="submitErrors.length" class="rounded-lg border border-destructive/40 bg-destructive/5 p-3 text-sm text-destructive">
            قبل از ثبت نهایی این موارد را کامل کنید: {{ submitErrors.join('، ') }}
          </p>
          <p class="text-xs text-muted-foreground">ثبت نهایی به معنی تأیید نیست؛ درخواست به مدیر ارسال می‌شود و تا تصمیم او در وضعیت «در انتظار تأیید» می‌ماند.</p>
        </section>
      </div>

      <DialogFooter class="flex-row flex-wrap items-center justify-between gap-2 border-t px-4 py-3 sm:px-6">
        <div class="flex gap-2">
          <Button type="button" variant="outline" :disabled="step === 0 || saving" @click="back">قبلی</Button>
          <Button v-if="step < STEPS.length - 1" type="button" :disabled="saving" @click="next">بعدی</Button>
        </div>
        <div class="flex flex-wrap gap-2">
          <Button type="button" variant="outline" class="gap-2" :disabled="saving" @click="save(false)">
            <Icon name="lucide:save" class="size-4" /> ذخیره پیش‌نویس
          </Button>
          <Button v-if="step === STEPS.length - 1" type="button" class="gap-2" :disabled="saving" @click="save(true)">
            <Icon :name="saving ? 'lucide:loader-circle' : 'lucide:send'" class="size-4" :class="saving && 'animate-spin'" /> ثبت درخواست
          </Button>
        </div>
      </DialogFooter>
    </DialogContent>
  </Dialog>
</template>

<script setup lang="ts">
import type { CrmCustomerRef } from '~/stores/crm'
import type { SampleCustomer, SampleDetail, SampleFile } from '~/utils/requestSample'
import { DELIVERY_METHODS, PRIORITY_META, UNIT_OPTIONS } from '~/utils/requestSample'
import { formatJalali, todayIso, toPersianDigits } from '~/utils/jalali'
import { requestErrorMessage } from '~/utils/request-workflow'

const props = defineProps<{ open: boolean, requestId: number | null }>()
const emit = defineEmits<{ (e: 'update:open', v: boolean): void, (e: 'saved', id: number, submitted: boolean): void }>()

const store = useRequestSampleStore()
const customerStore = useCustomerStore()
const auth = useAuthStore()
const notify = useNotify()

const STEPS = [
  { key: 'customer', title: 'اطلاعات مشتری' }, { key: 'product', title: 'اطلاعات محصول' },
  { key: 'sample', title: 'مشخصات نمونه' }, { key: 'technical', title: 'کاربرد و اطلاعات فنی' },
  { key: 'shipping', title: 'اطلاعات ارسال' }, { key: 'review', title: 'بازبینی و ثبت' },
]
interface ItemForm {
  product_category: string, product_name: string, grade: string, alternative_product: string,
  specifications: string, quantity: string, unit: string, number_of_samples: string, packaging: string
}
const blankItem = (): ItemForm => ({ product_category: '', product_name: '', grade: '', alternative_product: '', specifications: '', quantity: '', unit: 'kg', number_of_samples: '1', packaging: '' })
const blankForm = () => ({
  sales_rep_user_id: null as number | null, priority: 'NORMAL', dispatch_ref_number: '', required_delivery_date: '',
  purpose: '', technical_requirements: '', application: '', industry: '', production_process: '', required_properties: '',
  delivery_method: '', recipient_name: '', delivery_address: '', country: 'ایران', city: '', postal_code: '',
  delivery_instructions: '', internal_notes: '', items: [blankItem()] as ItemForm[],
})
const form = reactive(blankForm())
const customer = ref<CrmCustomerRef | null>(null)
const customerInfo = ref<SampleCustomer | null>(null)
const lockedCustomer = ref(false)
const files = ref<Pick<SampleFile, 'id' | 'name'>[]>([])
const newFileIds = ref<string[]>([]) // uploaded in this session, not linked yet
const reps = ref<{ id: number, name: string }[]>([])
const err = reactive<Record<string, string>>({})
const step = ref(0)
const furthest = ref(0)
const saving = ref(false)
const uploading = ref(false)
const loadingExisting = ref(false)
const bodyEl = ref<HTMLElement | null>(null)
const fileInput = ref<HTMLInputElement | null>(null)

const repModel = computed({
  get: () => (form.sales_rep_user_id && form.sales_rep_user_id !== auth.user?.id ? String(form.sales_rep_user_id) : 'me'),
  set: (v: string) => { form.sales_rep_user_id = v === 'me' ? null : Number(v) },
})
const deliveryModel = computed({ get: () => form.delivery_method || undefined, set: (v: string | undefined) => { form.delivery_method = v ?? '' } })

const clearErr = () => Object.keys(err).forEach(k => delete err[k])
const toNum = (s: string) => Number(String(s).replace(/[۰-۹]/g, d => String('۰۱۲۳۴۵۶۷۸۹'.indexOf(d))).replace(/[٠-٩]/g, d => String('٠١٢٣٤٥٦٧٨٩'.indexOf(d))).replace(/[,٬]/g, '').trim())

function reset() {
  Object.assign(form, blankForm())
  customer.value = null
  customerInfo.value = null
  lockedCustomer.value = false
  files.value = []
  newFileIds.value = []
  clearErr()
  step.value = 0
  furthest.value = 0
}

async function populate(d: SampleDetail) {
  customer.value = { id: d.customer.id, name: d.customer.name, province: d.customer.province, industry: null }
  customerInfo.value = d.customer
  lockedCustomer.value = d.status !== 'DRAFT'
  Object.assign(form, {
    sales_rep_user_id: d.sales_rep.id, priority: d.priority, dispatch_ref_number: d.dispatch_ref_number ?? '',
    required_delivery_date: d.required_delivery_date ?? '', purpose: d.purpose ?? '', technical_requirements: d.technical_requirements ?? '',
    application: d.application ?? '', industry: d.industry ?? '', production_process: d.production_process ?? '',
    required_properties: d.required_properties ?? '', delivery_method: d.delivery_method ?? '', recipient_name: d.recipient_name ?? '',
    delivery_address: d.delivery_address ?? '', country: d.country ?? '', city: d.city ?? '', postal_code: d.postal_code ?? '',
    delivery_instructions: d.delivery_instructions ?? '', internal_notes: d.internal_notes ?? '',
    items: d.items.length ? d.items.map(i => ({
      product_category: i.product_category ?? '', product_name: i.product_name, grade: i.grade ?? '', alternative_product: i.alternative_product ?? '',
      specifications: i.specifications ?? '', quantity: i.quantity === null ? '' : String(i.quantity), unit: i.unit,
      number_of_samples: String(i.number_of_samples), packaging: i.packaging ?? '',
    })) : [blankItem()],
  })
  files.value = d.files.filter(f => f.kind === 'TECHNICAL').map(f => ({ id: f.id, name: f.name }))
  furthest.value = STEPS.length - 1
}

watch(() => props.open, async (v) => {
  if (!v) return
  reset()
  // consumed-product + grade pick-lists defined in the CRM customer bank
  customerStore.loadOptionItems(true)
  store.loadReps().then(r => (reps.value = r)).catch(() => {})
  if (props.requestId) {
    loadingExisting.value = true
    try { await populate(await store.get(props.requestId)) }
    catch (e) { notify.error(requestErrorMessage(e, 'بارگذاری درخواست انجام نشد.')); emit('update:open', false) }
    finally { loadingExisting.value = false }
  }
}, { immediate: true })

async function onCustomer(c: CrmCustomerRef | null) {
  customer.value = c
  customerInfo.value = null
  delete err.customer_id
  if (!c) return
  try {
    const full = await store.fetchCustomer(c.id)
    customerInfo.value = {
      id: c.id, name: c.name, brand: full.brand_name ?? null, province: full.factory_province ?? null, city: full.factory_city ?? null,
      company_name: full.company_name ?? null, company_phone: full.company_phone ?? null, category: full.category ?? null,
      contacts: (full.contacts ?? []).map((p: any) => ({ name: `${p.first_name ?? ''} ${p.last_name ?? ''}`.trim(), position: p.position ?? null, mobile: p.mobile ?? null, landline: p.landline ?? null })),
    }
    if (!form.recipient_name) form.recipient_name = customerInfo.value.contacts?.[0]?.name ?? ''
    if (!form.city && customerInfo.value.city) form.city = customerInfo.value.city
    if (!form.industry && full.category) form.industry = full.category
  }
  catch { /* the card is only a convenience */ }
}

const addItem = () => form.items.push(blankItem())
function removeItem(i: number) { if (form.items.length > 1) form.items.splice(i, 1) }

async function onFiles(ev: Event) {
  const input = ev.target as HTMLInputElement
  const picked = Array.from(input.files ?? [])
  input.value = ''
  uploading.value = true
  try {
    for (const f of picked) {
      const ref = await store.uploadFile(f, 'TECHNICAL', props.requestId ?? undefined)
      files.value.push({ id: ref.id, name: ref.name })
      if (!props.requestId) newFileIds.value.push(ref.id)
    }
  }
  catch (e) { notify.error(requestErrorMessage(e, 'بارگذاری فایل انجام نشد.')) }
  finally { uploading.value = false }
}
async function removeFile(id: string) {
  try { await store.deleteFile(id) }
  catch (e) { notify.error(requestErrorMessage(e, 'حذف فایل انجام نشد.')); return }
  files.value = files.value.filter(f => f.id !== id)
  newFileIds.value = newFileIds.value.filter(x => x !== id)
}

/* ── validation: per step (Next) and the whole form (Submit) ── */
function validateStep(i: number, into: Record<string, string> = err): boolean {
  let ok = true
  const bad = (k: string, m: string) => { into[k] = m; ok = false }
  if (i === 0) {
    if (!customer.value) bad('customer_id', 'مشتری را از بانک اطلاعات انتخاب کنید.')
    if (!form.dispatch_ref_number.trim()) bad('dispatch_ref_number', 'شمارهٔ حوالهٔ نمونه الزامی است.')
  }
  if (i === 1) {
    if (!form.items.length) bad('items', 'حداقل یک محصول اضافه کنید.')
    form.items.forEach((it, n) => { if (!it.product_name.trim()) bad(`items.${n}.product_name`, 'نام محصول را انتخاب کنید.') })
  }
  if (i === 2) {
    form.items.forEach((it, n) => {
      const q = toNum(it.quantity)
      if (!(q > 0)) bad(`items.${n}.quantity`, 'مقدار باید بیشتر از صفر باشد.')
      const c = toNum(it.number_of_samples)
      if (!Number.isInteger(c) || c < 1) bad(`items.${n}.number_of_samples`, 'تعداد باید عدد صحیح و حداقل ۱ باشد.')
    })
    if (form.required_delivery_date && form.required_delivery_date < todayIso()) bad('required_delivery_date', 'تاریخ نمی‌تواند در گذشته باشد.')
  }
  if (i === 4) {
    if (!form.recipient_name.trim()) bad('recipient_name', 'نام تحویل‌گیرنده الزامی است.')
    if (!form.delivery_address.trim()) bad('delivery_address', 'نشانی تحویل الزامی است.')
    if (!form.city.trim()) bad('city', 'شهر الزامی است.')
  }
  return ok
}
const submitErrors = computed(() => {
  const probe: Record<string, string> = {}
  ;[0, 1, 2, 4].forEach(i => validateStep(i, probe))
  return Object.values(probe)
})

function goTo(i: number) {
  if (i > furthest.value) return
  step.value = i
  bodyEl.value?.scrollTo({ top: 0 })
}
function next() {
  clearErr()
  if (!validateStep(step.value)) return
  step.value += 1
  furthest.value = Math.max(furthest.value, step.value)
  bodyEl.value?.scrollTo({ top: 0 })
}
const back = () => { step.value = Math.max(0, step.value - 1) }

const nz = (s: string) => (s.trim() ? s.trim() : null)
function payload() {
  return {
    customer_id: customer.value!.id,
    sales_rep_user_id: form.sales_rep_user_id,
    priority: form.priority,
    dispatch_ref_number: nz(form.dispatch_ref_number),
    required_delivery_date: form.required_delivery_date || null,
    purpose: nz(form.purpose), technical_requirements: nz(form.technical_requirements), application: nz(form.application),
    industry: nz(form.industry), production_process: nz(form.production_process), required_properties: nz(form.required_properties),
    delivery_method: nz(form.delivery_method), recipient_name: nz(form.recipient_name), delivery_address: nz(form.delivery_address),
    country: nz(form.country), city: nz(form.city), postal_code: nz(form.postal_code),
    delivery_instructions: nz(form.delivery_instructions), internal_notes: nz(form.internal_notes),
    items: form.items.filter(i => i.product_name.trim()).map(i => ({
      product_category: nz(i.product_category), product_name: i.product_name.trim(), grade: nz(i.grade),
      alternative_product: nz(i.alternative_product), specifications: nz(i.specifications),
      quantity: toNum(i.quantity) > 0 ? toNum(i.quantity) : 0.001, unit: i.unit,
      number_of_samples: Math.max(1, Math.round(toNum(i.number_of_samples)) || 1), packaging: nz(i.packaging),
    })),
    file_ids: newFileIds.value,
  }
}

async function save(submit: boolean) {
  clearErr()
  if (!customer.value) { step.value = 0; err.customer_id = 'مشتری را انتخاب کنید.'; return }
  if (submit) {
    const all: Record<string, string> = {}
    for (const i of [0, 1, 2, 4]) {
      if (!validateStep(i, all)) {
        Object.assign(err, all)
        step.value = i
        notify.error('برخی فیلدهای الزامی کامل نیست.')
        return
      }
    }
  }
  saving.value = true
  try {
    const body = payload()
    const saved = props.requestId ? await store.update(props.requestId, body) : await store.create(body)
    if (submit) await store.transition(saved.id, 'submit')
    emit('saved', saved.id, submit)
    emit('update:open', false)
  }
  catch (e) {
    notify.error(requestErrorMessage(e, 'ذخیرهٔ درخواست انجام نشد.'))
  }
  finally { saving.value = false }
}

/* review summary */
const itemsText = computed(() => form.items.filter(i => i.product_name).map(i => `${i.product_name}${i.grade ? ` · ${i.grade}` : ''} — ${i.quantity || '؟'} ${i.unit} × ${i.number_of_samples} بسته${i.packaging ? ` (${i.packaging})` : ''}${i.alternative_product ? ` | جایگزین: ${i.alternative_product}` : ''}`).join('\n'))
const summary = computed(() => [
  { title: 'اطلاعات مشتری', step: 0, rows: [
    { label: 'مشتری', value: customer.value?.name ?? '' }, { label: 'شمارهٔ حوالهٔ نمونه', value: form.dispatch_ref_number },
    { label: 'اولویت', value: PRIORITY_META[form.priority as keyof typeof PRIORITY_META]?.label ?? '' },
    { label: 'کارشناس فروش', value: repModel.value === 'me' ? 'خودم' : reps.value.find(r => String(r.id) === repModel.value)?.name ?? '' },
  ] },
  { title: 'محصولات و مشخصات نمونه', step: 1, rows: [
    { label: 'محصولات', value: itemsText.value, wide: true },
    { label: 'تاریخ موردنیاز', value: form.required_delivery_date ? toPersianDigits(formatJalali(form.required_delivery_date)) : '' },
    { label: 'هدف', value: form.purpose }, { label: 'الزامات فنی مشتری', value: form.technical_requirements, wide: true },
  ] },
  { title: 'مشخصات فنی و کاربرد', step: 3, rows: [
    { label: 'کاربرد نهایی', value: form.application }, { label: 'صنعت', value: form.industry },
    { label: 'فرآیند تولید', value: form.production_process, wide: true }, { label: 'ویژگی‌های موردنیاز', value: form.required_properties, wide: true },
    { label: 'پیوست‌ها', value: files.value.map(f => f.name).join('، '), wide: true },
  ] },
  { title: 'اطلاعات ارسال', step: 4, rows: [
    { label: 'روش تحویل', value: form.delivery_method }, { label: 'تحویل‌گیرنده', value: form.recipient_name },
    { label: 'نشانی', value: [form.country, form.city, form.delivery_address].filter(Boolean).join('، '), wide: true },
    { label: 'کد پستی', value: form.postal_code }, { label: 'توضیحات ارسال', value: form.delivery_instructions },
  ] },
])
</script>
