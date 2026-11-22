<!-- <PurchasesFlowDetail :request @updated="r => ..." @edit /> : one request with EVERY item on its own.
     What shows up per item is decided by the backend (`item.can.*`, `my_actions.*`), so each unit only gets its own
     operations: warehouse (receipt / delivered), procurement (supply place, quotations, shipping), manager (approve /
     return), finance (payment). Prices are not sent to a user without access, so nothing is hidden only in the UI. -->
<template>
  <div class="space-y-6">
    <div class="flex flex-wrap items-start justify-between gap-3">
      <div class="space-y-2">
        <div class="flex flex-wrap items-center gap-2">
          <h1 class="text-2xl font-semibold" dir="ltr">{{ request.request_no }}</h1>
          <PurchasesFlowBadge kind="request" :value="request.status" :label="request.status_label" />
        </div>
        <div class="flex flex-wrap gap-x-6 gap-y-1 text-sm text-muted-foreground">
          <span>واحد متقاضی: <b class="text-foreground">{{ request.requester_unit }}</b></span>
          <span>درخواست‌کننده: <b class="text-foreground">{{ request.requester_name }}</b></span>
          <span>تاریخ ثبت: <b class="text-foreground">{{ request.request_date_jalali }}</b></span>
          <span>تاریخ نیاز: <b class="text-foreground">{{ request.required_date_jalali }}</b></span>
        </div>
      </div>
      <div class="flex flex-wrap gap-2">
        <Button v-if="request.my_actions.can_edit" size="sm" class="gap-2" @click="emit('edit')"><Icon name="lucide:pencil" class="size-4" />اصلاح و ارسال مجدد</Button>
        <Button v-if="request.my_actions.can_finance_return" size="sm" class="gap-2" :disabled="busy" @click="run(() => store.financeReturn(request.id), 'درخواست به تدارکات ارجاع شد')"><Icon name="lucide:undo-2" class="size-4" />ارجاع به تدارکات</Button>
        <Button v-if="readyToSend.length" size="sm" class="gap-2" :disabled="busy" @click="run(() => store.submitToManager(request.id, readyToSend.map(i => i.id)), 'اقلام برای مدیر ارسال شد')"><Icon name="lucide:send" class="size-4" />ارسال {{ readyToSend.length }} قلم آماده برای مدیر</Button>
      </div>
    </div>

    <p v-if="request.status_note && ['RETURNED', 'VOID'].includes(request.status)" class="rounded-lg border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900"><b>{{ request.status === 'VOID' ? 'علت ابطال:' : 'موارد اصلاحی:' }}</b> {{ request.status_note }}</p>
    <p v-if="error" class="rounded-lg border border-destructive/40 bg-destructive/5 p-3 text-sm text-destructive">{{ error }}</p>

    <!-- procurement: request status -->
    <div v-if="request.my_actions.can_set_status" class="flex flex-wrap items-center gap-2 rounded-xl border bg-muted/30 p-3">
      <span class="text-sm font-semibold">وضعیت درخواست:</span>
      <button
        v-for="s in STATUS_CHOICES" :key="s.value" type="button" :disabled="busy"
        class="rounded-full border px-3 py-1 text-xs transition-colors hover:bg-muted" :class="request.status === s.value && 'border-primary bg-primary/10 font-semibold'"
        @click="changeStatus(s.value, s.label)"
      >{{ s.label }}</button>
      <span class="text-xs text-muted-foreground">پس از ارجاع کالاها به مالی، وضعیت کلی خودکار از وضعیت اقلام محاسبه می‌شود.</span>
    </div>

    <!-- at-a-glance counters -->
    <div class="grid grid-cols-2 gap-3 md:grid-cols-4">
      <div class="rounded-lg border p-3"><div class="text-xs text-muted-foreground">پرداخت‌شده</div><div class="text-xl font-semibold">{{ request.counts.PAID + request.counts.SHIPPING + request.counts.DELIVERED }}</div></div>
      <div class="rounded-lg border p-3"><div class="text-xs text-muted-foreground">در حال حمل</div><div class="text-xl font-semibold">{{ request.counts.SHIPPING }}</div></div>
      <div class="rounded-lg border p-3"><div class="text-xs text-muted-foreground">تحویل انبار شده</div><div class="text-xl font-semibold">{{ request.counts.DELIVERED }}</div></div>
      <div class="rounded-lg border p-3" :class="request.missing_receipts && 'border-orange-300 bg-orange-50'"><div class="text-xs text-muted-foreground">بدون رسید انبار</div><div class="text-xl font-semibold">{{ request.missing_receipts }}</div></div>
    </div>

    <!-- items -->
    <div class="space-y-4">
      <article v-for="it in request.items" :key="it.id" class="space-y-4 rounded-xl border p-4" :class="it.status === 'CANCELLED' && 'opacity-60'">
        <header class="flex flex-wrap items-start justify-between gap-2">
          <div>
            <h3 class="font-semibold">{{ it.name }} <span v-if="it.product_code" class="mr-1 text-xs font-normal text-muted-foreground" dir="ltr">{{ it.product_code }}</span></h3>
            <div class="mt-1 flex flex-wrap items-center gap-2">
              <PurchasesFlowBadge kind="item" :value="it.status" :label="it.status_label" />
              <PurchasesFlowBadge kind="priority" :value="it.priority" :label="it.priority_label" />
              <span v-if="it.supply_place_label" class="rounded-full bg-indigo-100 px-2.5 py-0.5 text-xs text-indigo-800">{{ it.supply_place_label }}</span>
              <span v-if="it.receipt_missing" class="rounded-full bg-orange-100 px-2.5 py-0.5 text-xs text-orange-800">رسید انبار ثبت نشده</span>
            </div>
          </div>
          <div v-if="it.timing" class="text-left text-xs" :class="it.timing.overdue || it.timing.on_time === false ? 'text-red-600' : 'text-muted-foreground'">
            <div>موعد تحویل: {{ it.timing.deadline }}</div>
            <div v-if="!it.timing.delivered">{{ it.timing.overdue ? `تأخیر: ${fmtHours(it.timing.delay_hours)}` : `باقی‌مانده: ${fmtHours(it.timing.remaining_hours)}` }}</div>
            <div v-else>{{ it.timing.on_time ? 'در موعد تحویل شد' : `با ${fmtHours(it.timing.delay_hours)} تأخیر` }}</div>
          </div>
        </header>

        <dl class="grid grid-cols-2 gap-x-4 gap-y-2 text-sm md:grid-cols-4">
          <div><dt class="text-xs text-muted-foreground">مقدار</dt><dd>{{ it.quantity }} {{ it.unit }}</dd></div>
          <div><dt class="text-xs text-muted-foreground">موجودی فعلی انبار</dt><dd>{{ it.current_stock ?? '—' }}</dd></div>
          <div><dt class="text-xs text-muted-foreground">نقطه سفارش</dt><dd>{{ it.reorder_point ?? '—' }}</dd></div>
          <div><dt class="text-xs text-muted-foreground">گروه کالایی</dt><dd>{{ it.category_name }}</dd></div>
          <div><dt class="text-xs text-muted-foreground">نوع درخواست</dt><dd>{{ it.request_type || '—' }}</dd></div>
          <div><dt class="text-xs text-muted-foreground">موضوع خرید</dt><dd>{{ it.purchase_subject_label || '—' }}</dd></div>
          <div v-if="it.approved_at"><dt class="text-xs text-muted-foreground">تأیید مدیر</dt><dd>{{ it.approved_at }}<span v-if="it.approved_by_name"> — {{ it.approved_by_name }}</span></dd></div>
          <div v-if="it.delivered_at"><dt class="text-xs text-muted-foreground">تحویل</dt><dd>{{ it.delivered_at }}</dd></div>
        </dl>
        <p v-if="it.status_note && ['INQUIRY', 'CANCELLED'].includes(it.status)" class="rounded-md bg-amber-50 p-2 text-xs text-amber-900">{{ it.status === 'CANCELLED' ? 'علت ابطال' : 'بازگشت از مدیر' }}: {{ it.status_note }}</p>

        <!-- procurement: supply place -->
        <div v-if="it.can.set_supply_place" class="flex items-center gap-3 text-sm">
          <span class="font-semibold">محل تأمین:</span>
          <label v-for="p in meta?.supply_places" :key="p.value" class="flex cursor-pointer items-center gap-1.5">
            <input type="radio" :name="`sp-${it.id}`" :checked="it.supply_place === p.value" :disabled="busy" @change="run(() => store.setSupplyPlace(request.id, it.id, p.value), 'محل تأمین ثبت شد')">{{ p.label }}
          </label>
        </div>

        <!-- quotations (only when the backend sent them) -->
        <div v-if="it.quotes" class="space-y-2">
          <div class="flex items-center justify-between">
            <h4 class="text-sm font-semibold">استعلام‌ها ({{ it.quotes.length }})</h4>
            <Button v-if="it.can.edit_quotes" variant="outline" size="sm" class="gap-1" @click="openQuote(it)"><Icon name="lucide:plus" class="size-4" />ثبت استعلام</Button>
          </div>
          <div v-if="it.quotes.length" class="overflow-x-auto rounded-lg border">
            <table class="w-full min-w-[640px] text-sm">
              <thead class="bg-muted/50 text-xs text-muted-foreground"><tr><th v-if="it.can.decide" class="w-8 p-2" /><th class="p-2 text-right">تأمین‌کننده</th><th class="p-2 text-right">قیمت واحد</th><th class="p-2 text-right">جمع</th><th class="p-2 text-right">پرداخت</th><th class="p-2 text-right">تحویل (روز)</th><th class="p-2 text-right">اعتبار / پیوست</th><th class="w-24 p-2" /></tr></thead>
              <tbody>
                <tr v-for="q in it.quotes" :key="q.id" class="border-t" :class="q.is_selected && 'bg-emerald-50'">
                  <td v-if="it.can.decide" class="p-2"><input v-model="pickedQuote[it.id]" type="radio" :name="`q-${it.id}`" :value="q.id"></td>
                  <td class="p-2">{{ q.supplier_name }}<span v-if="q.is_lowest" class="mr-1 rounded bg-emerald-100 px-1.5 text-[11px] text-emerald-800">کمترین</span><span v-if="q.is_selected" class="mr-1 rounded bg-blue-100 px-1.5 text-[11px] text-blue-800 dark:bg-blue-500/20 dark:text-blue-200">انتخاب مدیر</span></td>
                  <td class="p-2">{{ fmtMoney(q.unit_price) }}</td>
                  <td class="p-2">{{ fmtMoney(q.total_price) }}</td>
                  <td class="p-2">{{ q.payment_method_label || '—' }}</td>
                  <td class="p-2">{{ q.delivery_days ?? '—' }}</td>
                  <td class="p-2 text-xs">{{ q.validity_days ? `${q.validity_days} روز` : '' }} <button v-if="q.file" type="button" class="text-blue-700 hover:underline dark:text-blue-300" @click="pstore.downloadFile(q.file)">{{ q.file.name }}</button></td>
                  <td class="p-2 text-left">
                    <template v-if="it.can.edit_quotes"><button type="button" class="ml-2 text-xs text-blue-700 dark:text-blue-300" @click="openQuote(it, q)">ویرایش</button><button type="button" class="text-xs text-destructive" @click="run(() => store.deleteQuote(request.id, it.id, q.id), 'استعلام حذف شد')">حذف</button></template>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          <p v-else class="text-xs text-muted-foreground">هنوز استعلامی ثبت نشده است.</p>
        </div>

        <!-- payment -->
        <div v-if="it.payment" class="rounded-lg border bg-violet-50/50 p-3 text-sm">
          <h4 class="mb-2 font-semibold">پرداخت ({{ it.payment.method_label }})</h4>
          <dl class="grid grid-cols-2 gap-x-4 gap-y-1 md:grid-cols-4">
            <template v-if="it.payment.method === 'CASH'">
              <div><dt class="text-xs text-muted-foreground">تاریخ پرداخت</dt><dd>{{ it.payment.paid_date_jalali }}</dd></div>
              <div><dt class="text-xs text-muted-foreground">شناسه پرداخت</dt><dd dir="ltr" class="text-right">{{ it.payment.payment_ref }}</dd></div>
              <div><dt class="text-xs text-muted-foreground">رسید</dt><dd><button v-if="it.payment.receipt_file" type="button" class="text-blue-700 hover:underline dark:text-blue-300" @click="pstore.downloadFile(it.payment.receipt_file)">{{ it.payment.receipt_file.name }}</button></dd></div>
            </template>
            <template v-else>
              <div><dt class="text-xs text-muted-foreground">شمارهٔ چک</dt><dd dir="ltr" class="text-right">{{ it.payment.cheque_no }}</dd></div>
              <div><dt class="text-xs text-muted-foreground">مبلغ چک</dt><dd>{{ fmtMoney(it.payment.cheque_amount) }}</dd></div>
              <div><dt class="text-xs text-muted-foreground">تاریخ صدور / سررسید</dt><dd>{{ it.payment.cheque_issue_date_jalali }} / {{ it.payment.cheque_due_date_jalali }}</dd></div>
              <div><dt class="text-xs text-muted-foreground">تصویر چک</dt><dd><button v-if="it.payment.cheque_file" type="button" class="text-blue-700 hover:underline dark:text-blue-300" @click="pstore.downloadFile(it.payment.cheque_file)">{{ it.payment.cheque_file.name }}</button></dd></div>
              <div v-if="it.payment.cheque_bank"><dt class="text-xs text-muted-foreground">بانک</dt><dd>{{ it.payment.cheque_bank }}</dd></div>
              <div v-if="it.payment.cheque_payee"><dt class="text-xs text-muted-foreground">در وجه</dt><dd>{{ it.payment.cheque_payee }}</dd></div>
            </template>
            <div><dt class="text-xs text-muted-foreground">ثبت‌کننده</dt><dd>{{ it.payment.recorded_by_name }} — {{ it.payment.recorded_at }}</dd></div>
          </dl>
        </div>
        <p v-if="it.receipt" class="text-sm">رسید انبار: <button type="button" class="text-blue-700 hover:underline dark:text-blue-300" @click="pstore.downloadFile(it.receipt)">{{ it.receipt.name }}</button></p>

        <!-- actions of this item -->
        <div class="flex flex-wrap gap-2 border-t pt-3">
          <Button v-if="it.can.submit_to_manager" size="sm" :disabled="busy || !it.supply_place" :title="it.supply_place ? '' : 'ابتدا محل تأمین را مشخص کنید'" @click="run(() => store.submitToManager(request.id, [it.id]), 'کالا برای مدیر ارسال شد')">ارسال برای تأیید مدیر</Button>
          <template v-if="it.can.decide">
            <Button size="sm" :disabled="busy || !pickedQuote[it.id]" @click="openDecision(it, 'APPROVE')">تأیید گزینهٔ انتخاب‌شده</Button>
            <Button size="sm" variant="outline" :disabled="busy" @click="openDecision(it, 'RETURN')">بازگشت به تدارکات</Button>
          </template>
          <Button v-if="it.can.pay" size="sm" @click="openPayment(it)">ثبت پرداخت</Button>
          <Button v-if="it.can.ship" size="sm" variant="outline" :disabled="busy" @click="run(() => store.itemStatus(request.id, it.id, { status: 'SHIPPING' }), 'وضعیت «در حال حمل» ثبت شد')">در حال حمل</Button>
          <Button v-if="it.can.deliver" size="sm" variant="outline" @click="openFile(it, 'deliver')">ثبت تحویل به انبار</Button>
          <Button v-if="it.can.upload_receipt" size="sm" variant="outline" @click="openFile(it, 'receipt')">بارگذاری رسید انبار</Button>
          <Button v-if="it.can.cancel" size="sm" variant="outline" class="text-destructive" @click="openNote(it, 'cancel')">ابطال کالا</Button>
        </div>
      </article>
    </div>

    <!-- history -->
    <section v-if="request.events?.length" class="space-y-2">
      <h2 class="text-base font-semibold">تاریخچهٔ اقدامات</h2>
      <ol class="space-y-1 rounded-xl border p-3 text-sm">
        <li v-for="e in request.events" :key="e.id" class="flex flex-wrap gap-x-2 border-b py-1.5 last:border-0">
          <span class="text-xs text-muted-foreground">{{ e.at }}</span>
          <b>{{ e.user_name }}</b>
          <span v-if="e.item_name" class="rounded bg-muted px-1.5 text-xs">{{ e.item_name }}</span>
          <span v-if="e.to_label">{{ e.from_label ? `${e.from_label} ← ` : '' }}{{ e.to_label }}</span>
          <span v-if="e.note" class="text-muted-foreground">— {{ e.note }}</span>
        </li>
      </ol>
    </section>

    <!-- one dialog for every small form -->
    <Dialog :open="!!dlg" @update:open="v => { if (!v) dlg = null }">
      <DialogContent v-if="dlg" dir="rtl" class="max-h-[90vh] overflow-y-auto">
        <DialogHeader><DialogTitle>{{ dlgTitle }}</DialogTitle></DialogHeader>

        <div v-if="dlg.type === 'quote'" class="space-y-3">
          <PurchasesField label="تأمین‌کننده" required :error="errs.supplier_name || errs.supplier_id">
            <div class="relative">
              <Input v-model="qf.supplier_name" placeholder="جستجو در بانک تأمین‌کنندگان یا نوشتن نام…" @input="searchSup" @blur="closeSup" />
              <ul v-if="supOptions.length" class="absolute z-30 mt-1 max-h-48 w-full overflow-auto rounded-md border bg-background shadow">
                <li v-for="o in supOptions" :key="o.id" class="cursor-pointer px-3 py-2 text-sm hover:bg-muted" @mousedown.prevent="pickSup(o)">{{ o.name }}</li>
              </ul>
            </div>
          </PurchasesField>
          <div class="grid grid-cols-2 gap-3">
            <PurchasesField label="قیمت واحد پیشنهادی" required :error="errs.unit_price"><PurchasesMoney v-model="qf.unit_price" rial /></PurchasesField>
            <PurchasesField label="روش پرداخت" required :error="errs.payment_method">
              <select v-model="qf.payment_method" class="h-9 w-full rounded-md border border-input bg-transparent px-3 text-sm"><option value="">انتخاب کنید…</option><option v-for="m in meta?.pay_methods" :key="m.value" :value="m.value">{{ m.label }}</option></select>
            </PurchasesField>
            <PurchasesField label="تاریخ استعلام" :error="errs.received_date"><JalaliDateInput v-model="qf.received_date" /></PurchasesField>
            <PurchasesField label="مدت اعتبار (روز)"><Input v-model.number="qf.validity_days" type="number" min="0" /></PurchasesField>
            <PurchasesField label="زمان تحویل (روز)"><Input v-model.number="qf.delivery_days" type="number" min="0" /></PurchasesField>
          </div>
          <PurchasesField label="شرایط پرداخت"><Input v-model="qf.payment_terms" /></PurchasesField>
          <PurchasesField label="توضیحات"><Textarea v-model="qf.note" rows="2" /></PurchasesField>
          <PurchasesField label="پیوست (پیش‌فاکتور)"><PurchasesFiles v-model="files" :upload="pstore.upload" :download="pstore.downloadFile" :max="1" /></PurchasesField>
        </div>

        <div v-else-if="dlg.type === 'payment'" class="space-y-3">
          <PurchasesField label="روش پرداخت" required :error="errs.method">
            <select v-model="pf.method" class="h-9 w-full rounded-md border border-input bg-transparent px-3 text-sm"><option v-for="m in meta?.pay_methods" :key="m.value" :value="m.value">{{ m.label }}</option></select>
          </PurchasesField>
          <template v-if="pf.method === 'CASH'">
            <div class="grid grid-cols-2 gap-3">
              <PurchasesField label="تاریخ پرداخت" required :error="errs.paid_date"><JalaliDateInput v-model="pf.paid_date" /></PurchasesField>
              <PurchasesField label="شناسه پرداخت" required :error="errs.payment_ref"><Input v-model="pf.payment_ref" dir="ltr" class="text-right" /></PurchasesField>
            </div>
            <PurchasesField label="تصویر یا فایل رسید پرداخت" required :error="errs.receipt_file_id"><PurchasesFiles v-model="files" :upload="pstore.upload" :download="pstore.downloadFile" :max="1" /></PurchasesField>
          </template>
          <template v-else>
            <PurchasesField label="تصویر چک" required :error="errs.cheque_file_id"><PurchasesFiles v-model="files" :upload="pstore.upload" :download="pstore.downloadFile" :max="1" /></PurchasesField>
            <div class="grid grid-cols-2 gap-3">
              <PurchasesField label="شمارهٔ چک" required :error="errs.cheque_no"><Input v-model="pf.cheque_no" dir="ltr" class="text-right" /></PurchasesField>
              <PurchasesField label="مبلغ چک" required :error="errs.cheque_amount"><PurchasesMoney v-model="pf.cheque_amount" rial /></PurchasesField>
              <PurchasesField label="تاریخ صدور" required :error="errs.cheque_issue_date"><JalaliDateInput v-model="pf.cheque_issue_date" /></PurchasesField>
              <PurchasesField label="تاریخ سررسید" required :error="errs.cheque_due_date"><JalaliDateInput v-model="pf.cheque_due_date" /></PurchasesField>
              <PurchasesField label="بانک"><Input v-model="pf.cheque_bank" /></PurchasesField>
              <PurchasesField label="در وجه"><Input v-model="pf.cheque_payee" /></PurchasesField>
            </div>
          </template>
          <PurchasesField label="توضیحات"><Textarea v-model="pf.note" rows="2" /></PurchasesField>
        </div>

        <div v-else-if="dlg.type === 'file'" class="space-y-3">
          <p class="text-sm text-muted-foreground">{{ dlg.mode === 'deliver' ? 'تحویل این کالا به انبار ثبت می‌شود. رسید انبار را همین‌جا یا بعداً بارگذاری کنید؛ پس از ثبت، رسید قابل جایگزینی نیست.' : 'رسید انبار این کالا فقط یک بار ثبت می‌شود و قابل جایگزینی نیست.' }}</p>
          <PurchasesField label="رسید انبار" :required="dlg.mode === 'receipt'" :error="errs.file_id"><PurchasesFiles v-model="files" :upload="pstore.upload" :download="pstore.downloadFile" :max="1" /></PurchasesField>
        </div>

        <div v-else class="space-y-3">
          <p v-if="dlg.type === 'decision' && dlg.action === 'APPROVE'" class="text-sm text-muted-foreground">پس از تأیید، این کالا برای پرداخت به واحد مالی ارجاع می‌شود. اگر گزینهٔ ارزان‌تر موجود است، دلیل انتخاب را بنویسید.</p>
          <PurchasesField :label="noteLabel" :required="noteRequired" :error="errs.note"><Textarea v-model="note" rows="3" /></PurchasesField>
        </div>

        <p v-if="dlgError" class="text-sm text-destructive">{{ dlgError }}</p>
        <DialogFooter><Button variant="outline" @click="dlg = null">انصراف</Button><Button :disabled="busy" @click="submitDialog">ثبت</Button></DialogFooter>
      </DialogContent>
    </Dialog>
  </div>
</template>

<script setup lang="ts">
import { ApiError } from '~/services/backendApi'
import type { PFile } from '~/utils/purchase'
import type { FlowItem, FlowQuote, FlowRequest } from '~/utils/purchaseFlow'

const props = defineProps<{ request: FlowRequest }>()
const emit = defineEmits<{ (e: 'updated', r: FlowRequest): void, (e: 'edit'): void }>()
const store = usePurchaseFlowStore()
const pstore = usePurchasesStore()
const notify = useNotify()
const meta = computed(() => store.meta)
await store.loadMeta()

const STATUS_CHOICES = [
  { value: 'UNDER_REVIEW', label: 'در حال بررسی' }, { value: 'SOURCING', label: 'در حال استعلام و تأمین' },
  { value: 'RETURNED', label: 'استرداد جهت اصلاح' }, { value: 'VOID', label: 'ابطال' },
]
const busy = ref(false)
const error = ref('')
const readyToSend = computed(() => props.request.items.filter(i => i.can.submit_to_manager && i.supply_place))
const pickedQuote = reactive<Record<number, number | undefined>>({})

async function run(fn: () => Promise<FlowRequest>, ok: string): Promise<boolean> {
  busy.value = true
  error.value = ''
  try { emit('updated', await fn()); notify.success(ok); return true }
  catch (e) { error.value = e instanceof ApiError ? e.message : 'عملیات انجام نشد.'; return false }
  finally { busy.value = false }
}

// ── dialogs ──
type Dlg = { type: 'quote', item: FlowItem, quote?: FlowQuote } | { type: 'payment', item: FlowItem } | { type: 'file', item: FlowItem, mode: 'deliver' | 'receipt' }
  | { type: 'decision', item: FlowItem, action: 'APPROVE' | 'RETURN' } | { type: 'note', item?: FlowItem, mode: 'cancel' | 'status', status?: string }
const dlg = ref<Dlg | null>(null)
const errs = ref<Record<string, string>>({})
const dlgError = ref('')
const files = ref<PFile[]>([])
const note = ref('')
const qf = reactive({ supplier_id: null as number | null, supplier_name: '', unit_price: null as number | null, payment_method: '', received_date: '', validity_days: null as number | null, delivery_days: null as number | null, payment_terms: '', note: '' })
const pf = reactive({ method: 'CASH', paid_date: '', payment_ref: '', cheque_no: '', cheque_amount: null as number | null, cheque_issue_date: '', cheque_due_date: '', cheque_bank: '', cheque_payee: '', note: '' })
const noteRequired = computed(() => !!dlg.value && ((dlg.value.type === 'decision' && dlg.value.action === 'RETURN') || dlg.value.type === 'note'))
const noteLabel = computed(() => (dlg.value?.type === 'decision' ? (dlg.value.action === 'RETURN' ? 'دلیل بازگشت به تدارکات' : 'توضیح / دلیل انتخاب') : 'دلیل'))
const dlgTitle = computed(() => {
  const d = dlg.value
  if (!d) return ''
  return ({ quote: d.type === 'quote' && d.quote ? 'ویرایش استعلام' : 'ثبت استعلام', payment: 'ثبت پرداخت', file: d.type === 'file' && d.mode === 'deliver' ? 'ثبت تحویل به انبار' : 'رسید انبار',
    decision: d.type === 'decision' && d.action === 'APPROVE' ? 'تأیید مدیر' : 'بازگشت به تدارکات', note: d.type === 'note' && d.mode === 'cancel' ? 'ابطال کالا' : 'تغییر وضعیت درخواست' } as Record<string, string>)[d.type]
})
function reset(d: Dlg) { dlg.value = d; errs.value = {}; dlgError.value = ''; files.value = []; note.value = '' }

function openQuote(item: FlowItem, quote?: FlowQuote) {
  reset({ type: 'quote', item, quote })
  Object.assign(qf, { supplier_id: quote?.supplier_id ?? null, supplier_name: quote?.supplier_name ?? '', unit_price: quote?.unit_price ?? null, payment_method: quote?.payment_method ?? '',
    received_date: quote?.received_date ?? '', validity_days: quote?.validity_days ?? null, delivery_days: quote?.delivery_days ?? null, payment_terms: quote?.payment_terms ?? '', note: quote?.note ?? '' })
  if (quote?.file) files.value = [quote.file]
}
function openPayment(item: FlowItem) {
  reset({ type: 'payment', item })
  Object.assign(pf, { method: item.payment_method || 'CASH', paid_date: '', payment_ref: '', cheque_no: '', cheque_amount: item.selected_total ?? null, cheque_issue_date: '', cheque_due_date: '', cheque_bank: '', cheque_payee: '', note: '' })
}
const openFile = (item: FlowItem, mode: 'deliver' | 'receipt') => reset({ type: 'file', item, mode })
const openDecision = (item: FlowItem, action: 'APPROVE' | 'RETURN') => reset({ type: 'decision', item, action })
const openNote = (item: FlowItem, mode: 'cancel') => reset({ type: 'note', item, mode })
function changeStatus(status: string, label: string) {
  if (status === props.request.status) return
  if (status === 'RETURNED' || status === 'VOID') reset({ type: 'note', mode: 'status', status })
  else run(() => store.setStatus(props.request.id, status), `وضعیت «${label}» ثبت شد`)
}

// supplier bank suggestions
const supOptions = ref<{ id: number, name: string }[]>([])
let timer: ReturnType<typeof setTimeout> | undefined
function searchSup() {
  qf.supplier_id = null
  clearTimeout(timer)
  timer = setTimeout(async () => { try { supOptions.value = await pstore.searchSuppliers(qf.supplier_name) } catch { supOptions.value = [] } }, 250)
}
const pickSup = (o: { id: number, name: string }) => { qf.supplier_id = o.id; qf.supplier_name = o.name; supOptions.value = [] }
const closeSup = () => setTimeout(() => { supOptions.value = [] }, 120)

async function submitDialog() {
  const d = dlg.value
  if (!d) return
  errs.value = {}
  dlgError.value = ''
  const id = props.request.id
  const fileId = files.value[0]?.id
  try {
    busy.value = true
    let r: FlowRequest
    let ok = 'ثبت شد'
    if (d.type === 'quote') {
      const body = { supplier_id: qf.supplier_id, supplier_name: qf.supplier_id ? null : qf.supplier_name, unit_price: qf.unit_price, payment_method: qf.payment_method || null, received_date: qf.received_date || null,
        validity_days: qf.validity_days || null, delivery_days: qf.delivery_days || null, payment_terms: qf.payment_terms, note: qf.note, file_id: files.value[0] && files.value[0].id !== d.quote?.file?.id ? fileId : null }
      r = await store.saveQuote(id, d.item.id, body, d.quote?.id)
      ok = 'استعلام ثبت شد'
    }
    else if (d.type === 'payment') {
      r = await store.pay(id, d.item.id, pf.method === 'CASH'
        ? { method: 'CASH', paid_date: pf.paid_date || null, payment_ref: pf.payment_ref, receipt_file_id: fileId ?? null, note: pf.note }
        : { method: 'CHEQUE', cheque_file_id: fileId ?? null, cheque_no: pf.cheque_no, cheque_amount: pf.cheque_amount, cheque_issue_date: pf.cheque_issue_date || null, cheque_due_date: pf.cheque_due_date || null, cheque_bank: pf.cheque_bank, cheque_payee: pf.cheque_payee, note: pf.note })
      ok = 'پرداخت ثبت شد؛ برای بازگشت به تدارکات «ارجاع به تدارکات» را بزنید'
    }
    else if (d.type === 'file') {
      r = d.mode === 'deliver' ? await store.itemStatus(id, d.item.id, { status: 'DELIVERED', file_id: fileId ?? null }) : await store.receipt(id, d.item.id, fileId ?? '')
      ok = d.mode === 'deliver' ? 'تحویل کالا ثبت شد' : 'رسید انبار ثبت شد'
    }
    else if (d.type === 'decision') {
      r = await store.decide(id, d.item.id, { action: d.action, quote_id: d.action === 'APPROVE' ? pickedQuote[d.item.id] : null, note: note.value.trim() || null })
      ok = d.action === 'APPROVE' ? 'کالا تأیید و به مالی ارجاع شد' : 'کالا به تدارکات بازگشت'
    }
    else if (d.mode === 'cancel' && d.item) { r = await store.itemStatus(id, d.item.id, { status: 'CANCELLED', note: note.value.trim() || null }); ok = 'کالا ابطال شد' }
    else { r = await store.setStatus(id, d.status ?? '', note.value.trim()); ok = 'وضعیت ثبت شد' }
    emit('updated', r)
    notify.success(ok)
    dlg.value = null
  }
  catch (e) {
    errs.value = e instanceof ApiError ? fieldErrors(e.details) : {}
    dlgError.value = e instanceof ApiError ? e.message : 'ثبت انجام نشد.'
  }
  finally { busy.value = false }
}
</script>
