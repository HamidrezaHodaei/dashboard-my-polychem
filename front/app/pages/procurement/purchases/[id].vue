<template>
  <ContainerWrapper class="space-y-6 py-6 md:py-8">
    <div class="flex flex-wrap items-start justify-between gap-3 border-b pb-5">
      <div>
        <div class="mb-2 flex items-center gap-2 text-xs text-muted-foreground">
          <NuxtLink to="/procurement/purchases" class="hover:text-foreground">گزارشات خرید</NuxtLink>
          <Icon name="lucide:chevron-left" class="size-3" /><span>{{ req ? req.request_no : 'خرید جدید' }}</span>
        </div>
        <h1 class="text-2xl font-semibold tracking-tight">{{ req?.subject || 'ثبت خرید جدید' }}</h1>
        <div v-if="req" class="mt-2 flex flex-wrap items-center gap-2 text-sm">
          <span class="rounded-full px-2.5 py-0.5 text-xs" :class="statusTone[req.status]">{{ req.status_label }}</span>
          <span class="text-muted-foreground">اولویت: {{ req.priority_label }}</span>
          <span v-if="saving" class="text-xs text-muted-foreground">در حال ذخیره…</span>
          <span v-else-if="savedAt" class="text-xs text-muted-foreground">آخرین ذخیره: {{ savedAt }}</span>
        </div>
      </div>
      <div class="flex flex-wrap gap-2">
        <Button variant="outline" size="sm" class="gap-2" @click="showSummary = true"><Icon name="lucide:clipboard-list" class="size-4" />خلاصه اطلاعات</Button>
        <Button v-if="req?.my_actions.can_send_back" variant="outline" size="sm" @click="askNote('send-back')">ارسال برای اصلاح</Button>
        <Button v-if="req?.my_actions.can_cancel" variant="outline" size="sm" class="text-destructive" @click="askNote('cancel')">لغو خرید</Button>
        <Button v-if="req?.my_actions.can_delete" variant="outline" size="sm" class="text-destructive" @click="removeDraft">حذف</Button>
      </div>
    </div>

    <p v-if="loadError" class="rounded-lg border border-destructive/40 bg-destructive/5 p-3 text-sm text-destructive">{{ loadError }}</p>
    <p v-if="req?.status_note && (req.status === 'NEEDS_REVISION' || req.status === 'CANCELLED')" class="rounded-lg border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900">
      <b>{{ req.status === 'CANCELLED' ? 'علت لغو:' : 'موارد اصلاحی:' }}</b> {{ req.status_note }}
    </p>
    <p v-if="readonly && req" class="rounded-lg border bg-muted/40 p-3 text-sm text-muted-foreground">
      این درخواست {{ closed ? 'بسته شده' : 'برای شما فقط‌خواندنی' }} است؛ {{ closed && req.my_actions.can_reopen ? 'برای ویرایش، آن را «ارسال برای اصلاح» کنید.' : '' }}
    </p>
    <div v-if="req?.my_actions.can_reopen" class="print-hide" />

    <!-- progress -->
    <div class="space-y-3">
      <Progress :model-value="((step + 1) / 6) * 100" class="h-1.5" />
      <ol class="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-6">
        <li v-for="(s, i) in WIZARD_STEPS" :key="s.key">
          <button
            type="button" class="flex w-full items-center gap-2 rounded-lg border p-2.5 text-right text-sm transition-colors hover:bg-muted"
            :class="[i === step && 'border-primary bg-primary/5', locked(i) && 'opacity-50']" @click="go(i)"
          >
            <span class="flex size-6 shrink-0 items-center justify-center rounded-full text-xs" :class="done(i) ? 'bg-emerald-500 text-white' : i === step ? 'bg-primary text-primary-foreground' : 'bg-muted'">
              <Icon v-if="done(i)" name="lucide:check" class="size-3.5" /><template v-else>{{ count(i + 1) }}</template>
            </span>
            <span class="leading-tight">{{ s.title }}</span>
          </button>
        </li>
      </ol>
    </div>

    <p v-if="stepError" class="rounded-lg border border-destructive/40 bg-destructive/5 p-3 text-sm text-destructive">{{ stepError }}</p>

    <div class="grid gap-6 lg:grid-cols-[1fr_300px]">
      <Card class="gap-5 p-5 shadow-none">
        <fieldset :disabled="readonly" class="min-w-0 space-y-5">
          <!-- 1: basic -->
          <section v-show="step === 0" class="grid gap-4 sm:grid-cols-2">
            <PurchasesField label="شماره درخواست خرید" hint="به‌صورت خودکار و یکتا تولید می‌شود"><Input :model-value="req?.request_no || 'پس از ثبت تولید می‌شود'" disabled dir="ltr" class="text-right" /></PurchasesField>
            <PurchasesField label="تاریخ ثبت" required :error="e('request_date')"><JalaliDateInput v-model="basic.request_date" /></PurchasesField>
            <PurchasesField label="شرکت یا واحد متقاضی" required :error="e('requester_unit')">
              <Input v-model="basic.requester_unit" list="req-units" />
              <datalist id="req-units"><option v-for="u in store.meta?.requester_units" :key="u" :value="u" /></datalist>
            </PurchasesField>
            <PurchasesField label="نام درخواست‌کننده" required :error="e('requester_name')"><Input v-model="basic.requester_name" /></PurchasesField>
            <PurchasesField label="موضوع خرید" required :error="e('subject')" class="sm:col-span-2"><Input v-model="basic.subject" /></PurchasesField>
            <PurchasesField label="اولویت خرید" required>
              <select v-model="basic.priority" :class="selectCls"><option v-for="p in store.meta?.priorities" :key="p.value" :value="p.value">{{ p.label }}</option></select>
            </PurchasesField>
            <div />
            <PurchasesField label="علت و ضرورت خرید" required :error="e('reason')" class="sm:col-span-2"><Textarea v-model="basic.reason" rows="3" /></PurchasesField>
            <PurchasesField label="توضیحات تکمیلی" class="sm:col-span-2"><Textarea v-model="basic.description" rows="3" /></PurchasesField>
          </section>

          <!-- 2: items -->
          <section v-show="step === 1" class="space-y-4">
            <p v-if="e('items')" class="text-sm text-destructive">{{ e('items') }}</p>
            <div v-for="(it, i) in items" :key="it.key" class="space-y-3 rounded-xl border p-4">
              <div class="flex items-center justify-between"><h4 class="text-sm font-semibold">قلم {{ count(i + 1) }}</h4>
                <Button v-if="!structureLocked" variant="ghost" size="sm" class="text-destructive" @click="items.splice(i, 1)">حذف قلم</Button></div>
              <div class="grid gap-3 sm:grid-cols-2">
                <PurchasesField label="گروه کالایی" required :error="e(`items.${i}.category_id`)">
                  <select v-model="it.category_id" :class="selectCls"><option :value="null" disabled>انتخاب…</option><option v-for="c in store.meta?.categories" :key="c.id" :value="c.id">{{ c.name }}</option></select>
                </PurchasesField>
                <PurchasesField label="نام کالا" required :error="e(`items.${i}.name`)"><Input v-model="it.name" /></PurchasesField>
                <PurchasesField label="برند یا مدل"><Input v-model="it.brand_model" /></PurchasesField>
                <div class="grid grid-cols-2 gap-3">
                  <PurchasesField label="تعداد" required :error="e(`items.${i}.quantity`)"><PurchasesMoney v-model="it.quantity" :decimals="3" /></PurchasesField>
                  <PurchasesField label="واحد" required :error="e(`items.${i}.unit`)">
                    <Input v-model="it.unit" list="units" /><datalist id="units"><option v-for="u in store.meta?.units" :key="u" :value="u" /></datalist>
                  </PurchasesField>
                </div>
                <PurchasesField label="مشخصات و شرح فنی" class="sm:col-span-2"><Textarea v-model="it.specs" rows="2" /></PurchasesField>
                <PurchasesField label="قیمت تخمینی واحد"><PurchasesMoney v-model="it.estimated_unit_price" /></PurchasesField>
                <PurchasesField label="مبلغ برآوردی قلم"><Input :model-value="it.quantity && it.estimated_unit_price ? money(it.quantity * it.estimated_unit_price) : '—'" disabled /></PurchasesField>
              </div>
              <details class="rounded-lg bg-muted/30 p-3 text-sm">
                <summary class="cursor-pointer font-medium">قیمت مبنا برای محاسبهٔ صرفه‌جویی (اختیاری)
                  <Badge v-if="it.reference_approved" class="mr-2 bg-emerald-100 text-emerald-800">تأییدشده</Badge>
                  <Badge v-else-if="it.reference_unit_price" variant="outline" class="mr-2">در انتظار تأیید</Badge>
                </summary>
                <p class="mt-2 text-xs text-muted-foreground">صرفه‌جویی فقط نسبت به قیمت مبنای مشخص، مستندشده و تأییدشده محاسبه می‌شود؛ برآورد تأییدنشده مبنا نیست.</p>
                <div class="mt-3 grid gap-3 sm:grid-cols-2">
                  <PurchasesField label="منبع قیمت مبنا" :error="e(`items.${i}.reference_source`)">
                    <select v-model="it.reference_source" :class="selectCls"><option :value="null">بدون قیمت مبنا</option><option v-for="s in referenceSources" :key="s.value" :value="s.value">{{ s.label }}</option></select>
                  </PurchasesField>
                  <PurchasesField label="قیمت مبنای واحد" :error="e(`items.${i}.reference_unit_price`)"><PurchasesMoney v-model="it.reference_unit_price" /></PurchasesField>
                  <PurchasesField label="مستند / شرح منبع" class="sm:col-span-2" :error="e(`items.${i}.reference_note`)"><Input v-model="it.reference_note" placeholder="مثلاً شمارهٔ قرارداد یا لیست قیمت" /></PurchasesField>
                </div>
                <Button v-if="it.id && it.reference_unit_price && !it.reference_approved && req?.my_actions.can_approve" size="sm" variant="outline" class="mt-3" @click="approveRef(it.id)">تأیید قیمت مبنا</Button>
              </details>
            </div>
            <Button v-if="!structureLocked" variant="outline" class="gap-2" @click="addItem"><Icon name="lucide:plus" class="size-4" />افزودن قلم کالا</Button>
            <p v-else class="text-xs text-muted-foreground">پس از ثبت استعلام، افزودن یا حذف قلم ممکن نیست؛ ویرایش مشخصات اقلام موجود آزاد است.</p>
          </section>

          <!-- 3: budget -->
          <section v-show="step === 2" class="grid gap-4 sm:grid-cols-2">
            <PurchasesField label="بودجه پیش‌بینی‌شده" :error="e('budget_amount')"><PurchasesMoney v-model="budget.budget_amount" /></PurchasesField>
            <PurchasesField label="مبلغ کل برآوردی" hint="جمع (تعداد × قیمت تخمینی) اقلام؛ وقتی همهٔ اقلام قیمت تخمینی داشته باشند"><Input :model-value="estimatedTotal === null ? '—' : money(estimatedTotal)" disabled /></PurchasesField>
            <PurchasesField label="تاریخ موردنیاز" required :error="e('required_date')"><JalaliDateInput v-model="budget.required_date" /></PurchasesField>
            <PurchasesField label="محل تحویل" required :error="e('delivery_location')"><Input v-model="budget.delivery_location" /></PurchasesField>
            <PurchasesField label="مستندات و فایل‌های مرتبط" class="sm:col-span-2" :error="e('files')">
              <PurchasesFiles v-model="budget.files" :upload="store.upload" :download="store.downloadFile" />
            </PurchasesField>
          </section>

          <!-- 4: inquiries -->
          <section v-show="step === 3" class="space-y-4">
            <p v-if="!req || ['DRAFT', 'ENTERING'].includes(req.status)" class="rounded-lg bg-amber-50 p-3 text-sm text-amber-900">ابتدا مراحل اول تا سوم را تکمیل کنید و با دکمهٔ «ثبت و ارسال به مرحله استعلام» ارسال نمایید.</p>
            <p v-if="e('inquiries')" class="text-sm text-destructive">{{ e('inquiries') }}</p>
            <div v-for="(q, i) in inquiries" :key="q.key" class="space-y-3 rounded-xl border p-4">
              <div class="flex items-center justify-between"><h4 class="text-sm font-semibold">استعلام {{ count(i + 1) }}</h4><Button variant="ghost" size="sm" class="text-destructive" @click="inquiries.splice(i, 1)">حذف</Button></div>
              <div class="grid gap-3 sm:grid-cols-2">
                <PurchasesField label="تأمین‌کننده (از بانک تأمین‌کنندگان)" required :error="e(`inquiries.${i}.supplier_id`)" class="relative">
                  <Input v-model="q.supplier_name" placeholder="جستجوی نام تأمین‌کننده…" @input="searchSup(q)" @focus="searchSup(q)" />
                  <ul v-if="q.options.length" class="absolute z-20 mt-1 max-h-48 w-full overflow-auto rounded-md border bg-background shadow">
                    <li v-for="o in q.options" :key="o.id" class="cursor-pointer px-3 py-2 text-sm hover:bg-muted" @click="pickSupplier(q, o)">{{ o.name }}<span v-if="o.category" class="text-xs text-muted-foreground"> — {{ o.category }}</span></li>
                  </ul>
                </PurchasesField>
                <PurchasesField label="تاریخ دریافت استعلام" required :error="e(`inquiries.${i}.received_date`)"><JalaliDateInput v-model="q.received_date" /></PurchasesField>
                <PurchasesField label="مدت اعتبار پیشنهاد (روز)" :error="e(`inquiries.${i}.validity_days`)"><PurchasesMoney v-model="q.validity_days" :decimals="0" /></PurchasesField>
                <PurchasesField label="زمان تحویل (روز)" :error="e(`inquiries.${i}.delivery_days`)"><PurchasesMoney v-model="q.delivery_days" :decimals="0" /></PurchasesField>
                <PurchasesField label="شرایط پرداخت" :error="e(`inquiries.${i}.payment_terms`)"><Input v-model="q.payment_terms" /></PurchasesField>
                <PurchasesField label="هزینه‌های جانبی"><PurchasesMoney v-model="q.extra_costs" /></PurchasesField>
              </div>
              <div class="overflow-x-auto">
                <table class="w-full text-sm">
                  <thead class="text-muted-foreground"><tr><th class="p-2 text-right">کالا</th><th class="p-2">تعداد</th><th class="p-2">قیمت پیشنهادی واحد</th><th class="p-2">جمع</th></tr></thead>
                  <tbody>
                    <tr v-for="it in savedItems" :key="it.id" class="border-t">
                      <td class="p-2">{{ it.name }}</td><td class="p-2 text-center">{{ count(it.quantity) }} {{ it.unit }}</td>
                      <td class="p-2"><PurchasesMoney v-model="q.prices[it.id!]" /></td>
                      <td class="p-2 text-center">{{ q.prices[it.id!] ? money((q.prices[it.id!] as number) * (it.quantity || 0)) : '—' }}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
              <p v-if="e(`inquiries.${i}.lines`)" class="text-xs text-destructive">{{ e(`inquiries.${i}.lines`) }}</p>
              <div class="grid gap-3 sm:grid-cols-2">
                <PurchasesField label="فایل پیش‌فاکتور یا استعلام"><PurchasesFiles v-model="q.files" :upload="store.upload" :download="store.downloadFile" :max="1" /></PurchasesField>
                <PurchasesField label="توضیحات تکمیلی"><Textarea v-model="q.note" rows="2" /></PurchasesField>
              </div>
              <p class="text-sm font-medium">جمع پیشنهاد (با هزینه‌های جانبی): {{ money(inquiryTotal(q)) }}</p>
            </div>
            <Button v-if="inquiries.length < (store.meta?.max_inquiries || 3) && savedItems.length" variant="outline" class="gap-2" @click="addInquiry"><Icon name="lucide:plus" class="size-4" />افزودن استعلام ({{ count(inquiries.length) }} از {{ count(store.meta?.max_inquiries || 3) }})</Button>
            <PurchasesField v-if="inquiries.length < (store.meta?.max_inquiries || 3)" label="علت عدم امکان اخذ سه استعلام" required :error="e('shortfall_reason')" hint="با کمتر از سه استعلام، تکمیل این فیلد برای نهایی‌کردن الزامی است">
              <Textarea v-model="shortfall" rows="2" />
            </PurchasesField>
            <PurchasesField v-else label="توضیح دربارهٔ استعلام‌ها (اختیاری)"><Textarea v-model="shortfall" rows="2" /></PurchasesField>
          </section>

          <!-- 5: compare + select -->
          <section v-show="step === 4" class="space-y-4">
            <p v-if="!req?.inquiries.length" class="rounded-lg bg-amber-50 p-3 text-sm text-amber-900">ابتدا استعلام‌ها را ثبت و نهایی کنید.</p>
            <div v-else class="overflow-x-auto">
              <table class="w-full text-sm">
                <thead class="bg-muted/50"><tr><th class="p-2 text-right">مقایسه</th>
                  <th v-for="q in req.inquiries" :key="q.id" class="p-2" :class="q.is_lowest && 'bg-emerald-50 text-emerald-800'">{{ q.supplier_name }}<div v-if="q.is_lowest" class="text-[11px]">کمترین قیمت</div></th></tr></thead>
                <tbody>
                  <tr v-for="it in req.items" :key="it.id" class="border-t"><td class="p-2">{{ it.name }} <span class="text-xs text-muted-foreground">({{ count(it.quantity) }} {{ it.unit }})</span></td>
                    <td v-for="q in req.inquiries" :key="q.id" class="p-2 text-center">{{ money(q.lines.find(l => l.item_id === it.id)?.unit_price) }}</td></tr>
                  <tr class="border-t"><td class="p-2">هزینه‌های جانبی</td><td v-for="q in req.inquiries" :key="q.id" class="p-2 text-center">{{ money(q.extra_costs) }}</td></tr>
                  <tr class="border-t font-semibold"><td class="p-2">جمع کل</td><td v-for="q in req.inquiries" :key="q.id" class="p-2 text-center" :class="q.is_lowest && 'bg-emerald-50'">{{ money(q.total_price) }}</td></tr>
                  <tr class="border-t"><td class="p-2">زمان تحویل (روز)</td><td v-for="q in req.inquiries" :key="q.id" class="p-2 text-center">{{ count(q.delivery_days) }}</td></tr>
                  <tr class="border-t"><td class="p-2">شرایط پرداخت</td><td v-for="q in req.inquiries" :key="q.id" class="p-2 text-center">{{ q.payment_terms || '—' }}</td></tr>
                  <tr class="border-t"><td class="p-2">انتخاب</td><td v-for="q in req.inquiries" :key="q.id" class="p-2 text-center">
                    <input v-model="sel.inquiry_id" type="radio" :value="q.id" :disabled="!q.lines_complete" @change="resetAgreed"></td></tr>
                </tbody>
              </table>
            </div>
            <template v-if="req?.inquiries.length">
              <p v-if="e('inquiry_id')" class="text-sm text-destructive">{{ e('inquiry_id') }}</p>
              <div class="space-y-2">
                <Label class="font-semibold">علت انتخاب <span class="text-destructive">*</span></Label>
                <div class="flex flex-wrap gap-4">
                  <label v-for="r in store.meta?.selection_reasons" :key="r.value" class="flex items-center gap-2 text-sm"><input v-model="sel.reasons" type="checkbox" :value="r.value">{{ r.label }}</label>
                </div>
                <p v-if="e('reasons')" class="text-xs text-destructive">{{ e('reasons') }}</p>
              </div>
              <p v-if="notLowest" class="rounded-lg bg-amber-50 p-3 text-sm text-amber-900">تأمین‌کنندهٔ انتخابی کمترین قیمت را نداده است؛ ثبت توضیح الزامی است.</p>
              <PurchasesField label="توضیح انتخاب تأمین‌کننده" :required="notLowest" :error="e('note')"><Textarea v-model="sel.note" rows="3" /></PurchasesField>
              <div v-if="selectedQuote" class="space-y-2">
                <Label class="font-semibold">قیمت نهایی توافق‌شده (واحد)</Label>
                <div v-for="it in req.items" :key="it.id" class="grid items-center gap-2 sm:grid-cols-[1fr_220px]">
                  <span class="text-sm">{{ it.name }} <span class="text-xs text-muted-foreground">— پیشنهاد: {{ money(selectedQuote.lines.find(l => l.item_id === it.id)?.unit_price) }}</span></span>
                  <PurchasesMoney v-model="sel.agreed[it.id]" />
                </div>
                <p class="text-sm font-medium">جمع توافقی اقلام: {{ money(agreedTotal) }}</p>
              </div>
            </template>
          </section>

          <!-- 6: result -->
          <section v-show="step === 5" class="space-y-4">
            <p v-if="!req?.selected_inquiry_id" class="rounded-lg bg-amber-50 p-3 text-sm text-amber-900">ابتدا تأمین‌کنندهٔ برنده را انتخاب کنید.</p>
            <template v-else>
              <div class="grid gap-4 sm:grid-cols-2">
                <PurchasesField label="تاریخ انجام خرید" required :error="e('purchase_date')"><JalaliDateInput v-model="result.purchase_date" /></PurchasesField>
                <PurchasesField label="وضعیت تحویل کالا" required :error="e('delivery_status')">
                  <select v-model="result.delivery_status" :class="selectCls"><option v-for="s in store.meta?.delivery_statuses" :key="s.value" :value="s.value">{{ s.label }}</option></select>
                </PurchasesField>
              </div>
              <div class="overflow-x-auto">
                <table class="w-full text-sm">
                  <thead class="text-muted-foreground"><tr><th class="p-2 text-right">کالا</th><th class="p-2">مقدار خریداری‌شده</th><th class="p-2">قیمت نهایی واحد</th><th class="p-2">جمع</th><th class="p-2">صرفه‌جویی</th></tr></thead>
                  <tbody>
                    <tr v-for="it in req.items" :key="it.id" class="border-t">
                      <td class="p-2">{{ it.name }}<div class="text-xs text-muted-foreground">سفارش: {{ count(it.quantity) }} {{ it.unit }}</div></td>
                      <td class="p-2"><PurchasesMoney v-model="result.qty[it.id]" :decimals="3" /></td>
                      <td class="p-2"><PurchasesMoney v-model="result.price[it.id]" /></td>
                      <td class="p-2 text-center">{{ money((result.qty[it.id] || 0) * (result.price[it.id] || 0)) }}</td>
                      <td class="p-2 text-center" :class="(saving_of(it) ?? 0) < 0 && 'text-destructive'">{{ saving_of(it) === null ? 'بدون قیمت مبنای تأییدشده' : money(saving_of(it)) }}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
              <p v-if="e('lines')" class="text-xs text-destructive">{{ e('lines') }}</p>
              <div class="grid gap-4 sm:grid-cols-2">
                <PurchasesField label="هزینه‌های جانبی"><PurchasesMoney v-model="result.extra" /></PurchasesField>
                <PurchasesField label="مبلغ نهایی خرید" hint="به‌صورت خودکار از اقلام و هزینه‌های جانبی محاسبه می‌شود"><Input :model-value="money(finalAmount)" disabled /></PurchasesField>
                <PurchasesField label="توضیحات نهایی" class="sm:col-span-2"><Textarea v-model="result.note" rows="3" /></PurchasesField>
                <PurchasesField label="مستندات نهایی" class="sm:col-span-2"><PurchasesFiles v-model="result.files" :upload="store.upload" :download="store.downloadFile" /></PurchasesField>
              </div>
            </template>
          </section>
        </fieldset>

        <!-- footer actions -->
        <div class="flex flex-wrap items-center justify-between gap-2 border-t pt-4">
          <div class="flex gap-2">
            <Button variant="outline" :disabled="step === 0" @click="go(step - 1)">مرحلهٔ قبل</Button>
            <Button v-if="!readonly" variant="outline" :disabled="saving" @click="save(false)">ذخیره پیش‌نویس</Button>
          </div>
          <div class="flex gap-2">
            <Button v-if="!readonly" :disabled="saving" @click="next">{{ nextLabel }}</Button>
            <Button v-else-if="step < 5" variant="outline" @click="go(step + 1)">مرحلهٔ بعد</Button>
          </div>
        </div>
      </Card>

      <!-- history: who did each step / status change and when -->
      <Card class="h-fit gap-3 p-4 shadow-none">
        <h3 class="text-sm font-semibold">تاریخچه</h3>
        <p v-if="!req" class="text-xs text-muted-foreground">پس از ثبت اولیه نمایش داده می‌شود.</p>
        <ol v-else class="max-h-[28rem] space-y-3 overflow-auto text-xs">
          <li v-for="ev in [...req.events].reverse()" :key="ev.id" class="border-r-2 pr-3" :class="ev.kind === 'STATUS' ? 'border-primary' : 'border-muted'">
            <div class="font-medium">{{ ev.kind === 'STATUS' ? `${ev.from_label ? `${ev.from_label} ← ` : ''}${ev.to_label}` : ev.kind === 'STEP' ? `ثبت مرحله: ${ev.step_label}` : ev.kind_label }}</div>
            <div v-if="ev.note" class="text-muted-foreground">{{ ev.note }}</div>
            <div class="text-muted-foreground">{{ ev.user_name || '—' }} — {{ ev.at }}</div>
          </li>
        </ol>
      </Card>
    </div>

    <!-- summary before the final submission -->
    <Dialog v-model:open="showSummary">
      <DialogContent class="max-h-[85vh] max-w-3xl overflow-y-auto" dir="rtl">
        <DialogHeader><DialogTitle>خلاصه اطلاعات خرید</DialogTitle></DialogHeader>
        <dl class="grid gap-x-6 gap-y-2 text-sm sm:grid-cols-2">
          <template v-for="row in summaryRows" :key="row[0]"><dt class="text-muted-foreground">{{ row[0] }}</dt><dd>{{ row[1] || '—' }}</dd></template>
        </dl>
        <table v-if="req?.items.length" class="mt-3 w-full text-xs">
          <thead class="text-muted-foreground"><tr><th class="p-1.5 text-right">کالا</th><th class="p-1.5">گروه</th><th class="p-1.5">تعداد</th><th class="p-1.5">برآورد</th><th class="p-1.5">قیمت نهایی</th></tr></thead>
          <tbody><tr v-for="it in req.items" :key="it.id" class="border-t text-center"><td class="p-1.5 text-right">{{ it.name }}</td><td>{{ it.category_name }}</td><td>{{ count(it.quantity) }} {{ it.unit }}</td><td>{{ money(it.estimated_total) }}</td><td>{{ money(it.final_unit_price) }}</td></tr></tbody>
        </table>
      </DialogContent>
    </Dialog>

    <!-- reason prompt (cancel / send back) -->
    <Dialog v-model:open="noteOpen">
      <DialogContent dir="rtl">
        <DialogHeader><DialogTitle>{{ noteAction === 'cancel' ? 'لغو خرید' : 'ارسال برای اصلاح' }}</DialogTitle></DialogHeader>
        <PurchasesField :label="noteAction === 'cancel' ? 'علت لغو' : 'موارد اصلاحی'" required :error="noteError"><Textarea v-model="noteText" rows="3" /></PurchasesField>
        <DialogFooter><Button variant="outline" @click="noteOpen = false">انصراف</Button><Button @click="submitNote">تأیید</Button></DialogFooter>
      </DialogContent>
    </Dialog>
  </ContainerWrapper>
</template>

<script setup lang="ts">
import { ApiError } from '~/services/backendApi'
import { WIZARD_STEPS, count, fieldErrors, money, statusTone } from '~/utils/purchase'
import type { PFile, PurchaseInquiry, PurchaseItem, PurchaseRequest, StepKey } from '~/utils/purchase'

definePageMeta({ title: 'ثبت و مدیریت خرید' })

const route = useRoute()
const store = usePurchasesStore()
const notify = useNotify()
const confirm = useConfirm()
const selectCls = 'h-9 w-full rounded-md border border-input bg-transparent px-3 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-60'

const idParam = computed(() => String(route.params.id))
const req = ref<PurchaseRequest | null>(null)
const step = ref(0)
const saving = ref(false)
const savedAt = ref('')
const loadError = ref('')
const stepError = ref('')
const errs = ref<Record<string, string>>({})
const e = (k: string) => errs.value[k]
const showSummary = ref(false)
const referenceSources = computed(() => (store.meta?.reference_sources ?? []).filter(s => s.value !== 'LAST_PURCHASE'))

const closed = computed(() => !!req.value && ['COMPLETED', 'CANCELLED'].includes(req.value.status))
const readonly = computed(() => !!req.value && !req.value.my_actions.can_edit)
const savedItems = computed(() => req.value?.items ?? [])
const structureLocked = computed(() => !!req.value?.inquiries.length)

/* ── per-step form state ── */
const basic = reactive({ request_date: '', requester_unit: '', requester_name: '', subject: '', priority: 'NORMAL', reason: '', description: '' })
type FormItem = PurchaseItem & { key: number }
let keySeq = 1
const blankItem = (): FormItem => ({ key: keySeq++, category_id: null, name: '', specs: null, brand_model: null, quantity: null, unit: '', estimated_unit_price: null, reference_unit_price: null, reference_source: null, reference_note: null, reference_item_id: null })
const items = ref<FormItem[]>([blankItem()])
const addItem = () => items.value.push(blankItem())
const budget = reactive<{ budget_amount: number | null, required_date: string, delivery_location: string, files: PFile[] }>({ budget_amount: null, required_date: '', delivery_location: '', files: [] })
interface FormInquiry { key: number, supplier_id: number | null, supplier_name: string, received_date: string, validity_days: number | null, delivery_days: number | null, payment_terms: string, extra_costs: number | null, note: string, files: PFile[], prices: Record<number, number | null>, options: { id: number, name: string, category: string | null }[] }
const inquiries = ref<FormInquiry[]>([])
const shortfall = ref('')
const sel = reactive<{ inquiry_id: number | null, reasons: string[], note: string, agreed: Record<number, number | null> }>({ inquiry_id: null, reasons: [], note: '', agreed: {} })
const result = reactive<{ purchase_date: string, delivery_status: string, extra: number | null, note: string, files: PFile[], qty: Record<number, number | null>, price: Record<number, number | null> }>({ purchase_date: '', delivery_status: 'NOT_DELIVERED', extra: null, note: '', files: [], qty: {}, price: {} })

const estimatedTotal = computed(() => {
  const list = items.value.filter(i => i.name || i.quantity)
  return list.length && list.every(i => i.estimated_unit_price !== null && i.quantity) ? list.reduce((s, i) => s + i.quantity! * i.estimated_unit_price!, 0) : null
})

/** Fill every form from the server copy. */
function hydrate(r: PurchaseRequest) {
  req.value = r
  Object.assign(basic, { request_date: r.request_date || '', requester_unit: r.requester_unit || '', requester_name: r.requester_name || '', subject: r.subject || '', priority: r.priority, reason: r.reason || '', description: r.description || '' })
  items.value = r.items.length ? r.items.map(i => ({ ...i, key: keySeq++ })) : [blankItem()]
  Object.assign(budget, { budget_amount: r.budget_amount, required_date: r.required_date || '', delivery_location: r.delivery_location || '', files: r.budget_files })
  inquiries.value = r.inquiries.map((q: PurchaseInquiry) => ({
    key: keySeq++, supplier_id: q.supplier_id, supplier_name: q.supplier_name, received_date: q.received_date || '', validity_days: q.validity_days, delivery_days: q.delivery_days,
    payment_terms: q.payment_terms || '', extra_costs: q.extra_costs, note: q.note || '', files: q.file ? [q.file] : [], options: [],
    prices: Object.fromEntries(q.lines.map(l => [l.item_id, l.unit_price])),
  }))
  shortfall.value = r.inquiry_shortfall_reason || ''
  sel.inquiry_id = r.selected_inquiry_id
  sel.reasons = [...r.selection_reasons]
  sel.note = r.selection_note || ''
  sel.agreed = Object.fromEntries(r.items.map(i => [i.id, i.final_unit_price ?? null]))
  result.purchase_date = r.purchase_date || ''
  result.delivery_status = r.delivery_status
  result.extra = r.final_extra_costs
  result.note = r.completion_note || ''
  result.files = r.final_files
  result.qty = Object.fromEntries(r.items.map(i => [i.id, i.purchased_quantity ?? i.quantity ?? null]))
  result.price = Object.fromEntries(r.items.map(i => [i.id, i.final_unit_price ?? null]))
  takeSnapshots()
}

/* ── step completion / locking ── */
const doneFlags = computed(() => {
  const r = req.value
  if (!r) return [false, false, false, false, false, false]
  const past = !['DRAFT', 'ENTERING'].includes(r.status)
  return [r.status !== 'DRAFT', r.items.length > 0 && r.current_step >= 2, past || (r.current_step >= 3 && !!r.required_date), r.inquiries_finalized, !!r.selected_inquiry_id && r.status !== 'AWAITING_SELECTION', r.status === 'COMPLETED' || r.status === 'AWAITING_DELIVERY']
})
const done = (i: number) => doneFlags.value[i]!
const locked = (i: number) => !req.value && i > 0
function go(i: number) {
  if (i < 0 || i > 5) return
  if (locked(i)) { notify.info('ابتدا اطلاعات اولیه را ذخیره کنید.'); return }
  stepError.value = ''
  errs.value = {}
  step.value = i
}

/* ── saving ── */
function body(key: StepKey, complete: boolean): Record<string, unknown> {
  const ids = (fs: PFile[]) => fs.map(f => ({ id: f.id }))
  if (key === 'basic') return { ...basic, request_date: basic.request_date || null, complete }
  if (key === 'items') {
    return {
      complete,
      items: items.value.map(i => ({
        id: i.id ?? null, category_id: i.category_id, name: i.name, specs: i.specs, brand_model: i.brand_model, quantity: i.quantity, unit: i.unit,
        estimated_unit_price: i.estimated_unit_price, reference_unit_price: i.reference_unit_price, reference_source: i.reference_source,
        reference_note: i.reference_note, reference_item_id: i.reference_item_id,
      })),
    }
  }
  if (key === 'budget') return { budget_amount: budget.budget_amount, required_date: budget.required_date || null, delivery_location: budget.delivery_location, files: ids(budget.files), complete }
  if (key === 'inquiries') {
    return {
      complete, shortfall_reason: shortfall.value,
      inquiries: inquiries.value.map(q => ({
        supplier_id: q.supplier_id, received_date: q.received_date || null, validity_days: q.validity_days, delivery_days: q.delivery_days,
        payment_terms: q.payment_terms, extra_costs: q.extra_costs, note: q.note, file_id: q.files[0]?.id ?? null,
        lines: Object.entries(q.prices).filter(([, p]) => p !== null && p !== undefined).map(([item_id, unit_price]) => ({ item_id: Number(item_id), unit_price })),
      })),
    }
  }
  if (key === 'selection') {
    return {
      complete, inquiry_id: sel.inquiry_id, reasons: sel.reasons, note: sel.note,
      lines: Object.entries(sel.agreed).filter(([, p]) => p !== null && p !== undefined).map(([item_id, final_unit_price]) => ({ item_id: Number(item_id), final_unit_price })),
    }
  }
  return {
    complete, purchase_date: result.purchase_date || null, delivery_status: result.delivery_status, final_extra_costs: result.extra, completion_note: result.note, files: ids(result.files),
    lines: Object.keys(result.qty).filter(k => result.qty[Number(k)] !== null && result.qty[Number(k)] !== undefined)
      .map(k => ({ item_id: Number(k), purchased_quantity: result.qty[Number(k)], final_unit_price: result.price[Number(k)] ?? null })),
  }
}

async function save(complete: boolean, silent = false): Promise<boolean> {
  if (readonly.value) return false
  const key = WIZARD_STEPS[step.value]!.key
  errs.value = {}
  stepError.value = ''
  saving.value = true
  try {
    let r: PurchaseRequest
    if (!req.value) {
      r = await store.create(body('basic', complete))
      await navigateTo(`/procurement/purchases/${r.id}`, { replace: true })
    }
    else {
      r = await store.saveStep(req.value.id, key, body(key, complete))
    }
    hydrate(r)
    savedAt.value = new Date().toLocaleTimeString('fa-IR', { hour: '2-digit', minute: '2-digit' })
    if (!silent && !complete) notify.success('پیش‌نویس ذخیره شد')
    return true
  }
  catch (err) {
    if (!silent) {
      errs.value = err instanceof ApiError ? fieldErrors(err.details) : {}
      stepError.value = err instanceof ApiError ? err.message : 'ذخیره انجام نشد.'
      if (err instanceof ApiError && Object.keys(errs.value).length) stepError.value = 'برخی فیلدها نیاز به اصلاح دارند؛ پیام‌ها زیر هر فیلد نمایش داده شده است.'
    }
    return false
  }
  finally { saving.value = false }
}

const nextLabel = computed(() => (step.value === 2 ? 'ثبت و ارسال به مرحله استعلام' : step.value === 3 ? 'نهایی‌کردن استعلام‌ها' : step.value === 4 ? 'ثبت تأمین‌کنندهٔ برنده' : step.value === 5 ? 'ثبت نهایی خرید' : 'ثبت و مرحلهٔ بعد'))
async function next() {
  if (!(await save(true))) return
  if (step.value === 2 && req.value && ['ENTERING', 'NEEDS_REVISION', 'DRAFT'].includes(req.value.status)) {
    try { hydrate(await store.action(req.value.id, 'submit')); notify.success('درخواست به مرحلهٔ استعلام ارسال شد') }
    catch (err) { stepError.value = err instanceof ApiError ? err.message : 'ارسال انجام نشد.'; errs.value = err instanceof ApiError ? fieldErrors(err.details) : {}; return }
  }
  if (step.value === 5) { showSummary.value = true; notify.success(req.value?.status === 'COMPLETED' ? 'خرید تکمیل شد' : 'اطلاعات خرید ثبت شد'); return }
  go(step.value + 1)
}

/* autosave: the current step is stored as a draft a few seconds after the last edit. A snapshot of what the
   server last returned stops it from saving (and re-hydrating) in a loop. */
let autoTimer: ReturnType<typeof setTimeout> | undefined
let snaps: string[] = []
const snapshot = (i: number) => JSON.stringify(body(WIZARD_STEPS[i]!.key, false))
function takeSnapshots() { nextTick(() => { snaps = WIZARD_STEPS.map((_, i) => snapshot(i)) }) }
function scheduleAutosave() {
  if (!req.value || readonly.value || saving.value || !snaps.length) return
  if (snapshot(step.value) === snaps[step.value]) return
  clearTimeout(autoTimer)
  autoTimer = setTimeout(() => { if (snapshot(step.value) !== snaps[step.value]) save(false, true) }, 2500)
}
watch([basic, items, budget, inquiries, shortfall, sel, result], scheduleAutosave, { deep: true })
onBeforeUnmount(() => clearTimeout(autoTimer))

/* ── inquiries helpers ── */
const newInquiry = (): FormInquiry => ({ key: keySeq++, supplier_id: null, supplier_name: '', received_date: '', validity_days: null, delivery_days: null, payment_terms: '', extra_costs: null, note: '', files: [], options: [], prices: {} })
const addInquiry = () => inquiries.value.push(newInquiry())
let supTimer: ReturnType<typeof setTimeout> | undefined
function searchSup(q: FormInquiry) {
  q.supplier_id = null // typing again means the previous pick no longer applies
  clearTimeout(supTimer)
  supTimer = setTimeout(async () => { try { q.options = await store.searchSuppliers(q.supplier_name) } catch { q.options = [] } }, 250)
}
function pickSupplier(q: FormInquiry, o: { id: number, name: string }) { q.supplier_id = o.id; q.supplier_name = o.name; q.options = [] }
const inquiryTotal = (q: FormInquiry) => savedItems.value.reduce((s, it) => s + (q.prices[it.id!] || 0) * (it.quantity || 0), 0) + (q.extra_costs || 0)

/* ── selection / result helpers ── */
const selectedQuote = computed(() => req.value?.inquiries.find(q => q.id === sel.inquiry_id) ?? null)
const lowestTotal = computed(() => { const t = (req.value?.inquiries ?? []).filter(q => q.lines_complete).map(q => q.total_price); return t.length ? Math.min(...t) : null })
const notLowest = computed(() => !!selectedQuote.value && lowestTotal.value !== null && selectedQuote.value.total_price > lowestTotal.value)
function resetAgreed() {
  const q = selectedQuote.value
  if (q) sel.agreed = Object.fromEntries(savedItems.value.map(i => [i.id, q.lines.find(l => l.item_id === i.id)?.unit_price ?? null]))
}
const agreedTotal = computed(() => savedItems.value.reduce((s, i) => s + (sel.agreed[i.id!] || 0) * (i.quantity || 0), 0))
const finalAmount = computed(() => savedItems.value.reduce((s, i) => s + (result.qty[i.id!] || 0) * (result.price[i.id!] || 0), 0) + (result.extra || 0))
function saving_of(it: PurchaseItem & { id: number }): number | null {
  if (!it.reference_approved || it.reference_unit_price === null || result.price[it.id] == null || result.qty[it.id] == null) return null
  return (it.reference_unit_price - result.price[it.id]!) * result.qty[it.id]!
}

/* ── actions ── */
async function approveRef(itemId: number) {
  if (!req.value) return
  try { hydrate(await store.action(req.value.id, 'approve-reference', { item_ids: [itemId] })); notify.success('قیمت مبنا تأیید شد') }
  catch (err) { notify.error('تأیید انجام نشد', err instanceof ApiError ? err.message : undefined) }
}
const noteOpen = ref(false)
const noteAction = ref<'cancel' | 'send-back'>('cancel')
const noteText = ref('')
const noteError = ref('')
function askNote(a: 'cancel' | 'send-back') { noteAction.value = a; noteText.value = ''; noteError.value = ''; noteOpen.value = true }
async function submitNote() {
  if (!req.value) return
  try { hydrate(await store.action(req.value.id, noteAction.value, { note: noteText.value })); noteOpen.value = false; notify.success(noteAction.value === 'cancel' ? 'خرید لغو شد' : 'برای اصلاح بازگردانده شد') }
  catch (err) { noteError.value = err instanceof ApiError ? err.message : 'انجام نشد.' }
}
async function removeDraft() {
  if (!req.value || !(await confirm.confirm({ title: 'حذف درخواست؟', description: 'این عمل قابل بازگشت نیست.', confirmLabel: 'حذف', tone: 'danger' }))) return
  try { await store.remove(req.value.id); await navigateTo('/procurement/purchases') }
  catch (err) { notify.error('حذف انجام نشد', err instanceof ApiError ? err.message : undefined) }
}

const summaryRows = computed<[string, string | number | null][]>(() => {
  const r = req.value
  if (!r) return []
  return [
    ['شماره درخواست', r.request_no], ['وضعیت', r.status_label], ['واحد متقاضی', r.requester_unit], ['درخواست‌کننده', r.requester_name],
    ['تاریخ ثبت', r.request_date_jalali], ['موضوع', r.subject], ['اولویت', r.priority_label], ['علت و ضرورت', r.reason],
    ['بودجه پیش‌بینی‌شده', r.budget_amount === null ? null : money(r.budget_amount)], ['مبلغ برآوردی', r.estimated_total === null ? null : money(r.estimated_total)],
    ['تاریخ موردنیاز', r.required_date_jalali], ['محل تحویل', r.delivery_location],
    ['تأمین‌کنندهٔ منتخب', r.inquiries.find(q => q.is_selected)?.supplier_name ?? null], ['علت انتخاب', r.selection_reason_labels?.join('، ') || null],
    ['مبلغ نهایی', r.final_amount === null ? null : money(r.final_amount)], ['وضعیت تحویل', r.delivery_label], ['صرفه‌جویی', r.savings === null ? 'بدون قیمت مبنای تأییدشده' : money(r.savings)],
    ['ثبت‌کننده', r.creator_name],
  ]
})

/** After a load, open the first step that still needs work. */
function firstOpenStep(r: PurchaseRequest) {
  if (['COMPLETED', 'CANCELLED'].includes(r.status)) return 5
  if (r.status === 'DRAFT' || r.status === 'ENTERING') return r.items.length ? 2 : 1
  if (r.status === 'AWAITING_INQUIRY' || r.status === 'INQUIRING') return 3
  if (r.status === 'AWAITING_SELECTION') return 4
  return 5
}

onMounted(async () => {
  await store.loadMeta().catch(() => {})
  if (idParam.value === 'new') {
    if (!store.can('create')) { loadError.value = 'مجوز ثبت خرید ندارید.'; return }
    basic.request_date = todayIso()
    return
  }
  try {
    const r = await store.fetchOne(Number(idParam.value))
    hydrate(r)
    step.value = Number(route.query.step) ? Number(route.query.step) - 1 : firstOpenStep(r)
  }
  catch (err) { loadError.value = err instanceof ApiError ? err.message : 'بارگذاری انجام نشد.' }
})
</script>
