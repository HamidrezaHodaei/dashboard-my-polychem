<template>
  <ContainerWrapper class="space-y-5 py-6 md:py-8">
    <div v-if="loading && !d" class="space-y-3">
      <Skeleton class="h-24 w-full" /><Skeleton class="h-64 w-full" />
    </div>
    <AppErrorState v-else-if="error" :message="error" @retry="load" />

    <template v-else-if="d">
      <!-- header -->
      <Card class="gap-4 p-5 shadow-none">
        <div class="flex flex-wrap items-start justify-between gap-3">
          <div class="space-y-2">
            <NuxtLink to="/crm/request-samples" class="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground">
              <Icon name="lucide:arrow-right" class="size-3.5" /> بازگشت به فهرست درخواست‌ها
            </NuxtLink>
            <div class="flex flex-wrap items-center gap-3">
              <h1 class="text-2xl font-semibold" dir="ltr">{{ d.code }}</h1>
              <RequestSampleStatusBadge :status="d.status" />
              <RequestSampleStatusBadge :status="d.priority" kind="priority" />
              <RequestSampleStatusBadge v-if="d.feedback_status" :status="d.feedback_status" kind="feedback" />
            </div>
            <div class="flex flex-wrap gap-x-6 gap-y-1 text-sm text-muted-foreground">
              <span>مشتری: <NuxtLink :to="`/crm/customers?open=${d.customer.id}`" class="font-medium text-foreground hover:underline" dir="auto">{{ d.customer.name }}</NuxtLink></span>
              <span>کارشناس مسئول: <b class="text-foreground">{{ d.sales_rep.name || '—' }}</b></span>
              <span>تاریخ ثبت: <b class="text-foreground">{{ fmtDate(d.requested_date) }}</b></span>
              <span v-if="d.created_by_name">ثبت‌کننده: <b class="text-foreground">{{ d.created_by_name }}</b></span>
            </div>
            <div v-if="d.parent || d.children.length" class="flex flex-wrap gap-2 text-xs">
              <NuxtLink v-if="d.parent" :to="`/crm/request-samples/${d.parent.id}`" class="rounded-full border px-2.5 py-0.5 hover:border-primary">
                ادامهٔ درخواست <span dir="ltr">{{ d.parent.code }}</span>
              </NuxtLink>
              <NuxtLink v-for="c in d.children" :key="c.id" :to="`/crm/request-samples/${c.id}`" class="rounded-full border px-2.5 py-0.5 hover:border-primary">
                درخواست مرتبط <span dir="ltr">{{ c.code }}</span>
              </NuxtLink>
            </div>
          </div>

          <!-- workflow actions (the server decides; buttons come from my_actions) -->
          <div class="flex flex-wrap items-center gap-2">
            <Button v-if="a.can_submit" class="gap-2" @click="doSubmit"><Icon name="lucide:send" class="size-4" /> ثبت نهایی و ارسال برای تأیید</Button>
            <Button v-if="a.can_approve" class="gap-2" @click="openReason('approve')"><Icon name="lucide:check-circle-2" class="size-4" /> تأیید</Button>
            <Button v-if="a.can_reject" variant="destructive" class="gap-2" @click="openReason('reject')"><Icon name="lucide:x-circle" class="size-4" /> رد</Button>
            <Button v-if="a.can_hold" variant="outline" class="gap-2" @click="openReason('hold')"><Icon name="lucide:pause-circle" class="size-4" /> توقف موقت</Button>
            <Button v-if="a.can_resume" variant="outline" class="gap-2" @click="openReason('resume')"><Icon name="lucide:play-circle" class="size-4" /> ازسرگیری</Button>
            <Button v-if="a.can_dispatch" class="gap-2" @click="dispatchOpen = true"><Icon name="lucide:truck" class="size-4" /> ثبت اطلاعات ارسال («ارسال‌شده»)</Button>
            <Button v-if="a.can_confirm_delivery" class="gap-2" @click="deliveryOpen = true"><Icon name="lucide:package-check" class="size-4" /> تأیید دریافت توسط مشتری</Button>
            <Button v-if="a.can_follow_up" variant="outline" class="gap-2" @click="openFollowUp(null)"><Icon name="lucide:phone-call" class="size-4" /> ثبت پیگیری</Button>
            <Button v-if="a.can_feedback" variant="outline" class="gap-2" @click="feedbackOpen = true"><Icon name="lucide:message-circle-heart" class="size-4" /> بازخورد نهایی</Button>
            <Button v-if="a.can_complete" variant="outline" class="gap-2" @click="openReason('complete')"><Icon name="lucide:badge-check" class="size-4" /> تکمیل درخواست</Button>
            <Button v-if="a.can_convert" class="gap-2 bg-green-600 hover:bg-green-700" @click="openReason('convert')"><Icon name="lucide:trending-up" class="size-4" /> تبدیل به فروش</Button>
            <Button v-if="a.can_new_request" variant="outline" class="gap-2" @click="newRequest"><Icon name="lucide:copy-plus" class="size-4" /> درخواست نمونهٔ جدید (مرتبط)</Button>
            <Button v-if="a.can_edit" variant="outline" class="gap-2" @click="wizardOpen = true"><Icon name="lucide:pencil" class="size-4" /> ویرایش</Button>
            <Button v-if="a.can_cancel" variant="ghost" class="gap-2 text-destructive hover:text-destructive" @click="openReason('cancel')"><Icon name="lucide:ban" class="size-4" /> لغو</Button>
            <Button v-if="a.can_delete" variant="ghost" size="icon" class="text-destructive hover:text-destructive" title="حذف" aria-label="حذف" @click="askDelete"><Icon name="lucide:trash-2" class="size-4" /></Button>
          </div>
        </div>

        <!-- progress stepper -->
        <ol class="flex w-full min-w-0 items-center gap-1 overflow-x-auto py-1" aria-label="مراحل درخواست">
          <template v-for="(s, i) in FLOW" :key="s.key">
            <li class="flex shrink-0 items-center gap-2" :aria-current="i === flowIndex ? 'step' : undefined">
              <span
                class="grid size-7 place-items-center rounded-full text-xs font-semibold"
                :class="i < flowIndex ? 'bg-primary text-primary-foreground' : i === flowIndex ? (offFlow ? 'bg-destructive text-white' : 'bg-primary text-primary-foreground ring-4 ring-primary/20') : 'bg-muted text-muted-foreground'"
              >
                <Icon v-if="i < flowIndex" name="lucide:check" class="size-3.5" />
                <template v-else>{{ i + 1 }}</template>
              </span>
              <span class="whitespace-nowrap text-xs" :class="i === flowIndex ? 'font-semibold' : 'text-muted-foreground'">{{ s.label }}</span>
            </li>
            <li v-if="i < FLOW.length - 1" class="h-0.5 min-w-6 flex-1 rounded-full" :class="i < flowIndex ? 'bg-primary' : 'bg-border'" aria-hidden="true" />
          </template>
        </ol>
        <p v-if="d.reject_reason" class="rounded-lg border border-destructive/30 bg-destructive/5 p-3 text-sm"><b>دلیل رد:</b> {{ d.reject_reason }}</p>
        <p v-if="d.hold_reason && d.status === 'ON_HOLD'" class="rounded-lg border border-orange-300 bg-orange-50 p-3 text-sm dark:bg-orange-950/30"><b>دلیل توقف:</b> {{ d.hold_reason }}</p>
        <p v-if="d.cancel_reason" class="rounded-lg border bg-muted/40 p-3 text-sm"><b>دلیل لغو:</b> {{ d.cancel_reason }}</p>
      </Card>

      <!-- tabs -->
      <div class="flex gap-2 overflow-x-auto pb-1" role="tablist">
        <button
          v-for="t in TABS" :key="t.key" type="button" role="tab" :aria-selected="tab === t.key"
          class="shrink-0 rounded-full border px-4 py-1.5 text-sm font-medium transition-colors"
          :class="tab === t.key ? 'border-primary bg-primary text-primary-foreground' : 'border-border hover:bg-muted'"
          @click="setTab(t.key)"
        >
          {{ t.label }}<span v-if="t.count" class="ms-1.5 rounded-full bg-black/10 px-1.5 text-[11px]">{{ toPersianDigits(t.count) }}</span>
        </button>
      </div>

      <!-- OVERVIEW -->
      <div v-show="tab === 'overview'" class="grid gap-5 lg:grid-cols-3">
        <Card class="gap-3 p-5 shadow-none lg:col-span-2">
          <h2 class="text-base font-semibold">خلاصهٔ درخواست</h2>
          <dl class="grid gap-x-6 gap-y-3 text-sm sm:grid-cols-2">
            <div v-for="r in overviewRows" :key="r.label" :class="r.wide && 'sm:col-span-2'">
              <dt class="text-xs text-muted-foreground">{{ r.label }}</dt>
              <dd class="whitespace-pre-line break-words" dir="auto">{{ r.value || '—' }}</dd>
            </div>
          </dl>
        </Card>
        <Card class="gap-3 p-5 shadow-none">
          <h2 class="text-base font-semibold">وضعیت پیگیری</h2>
          <div class="space-y-2 text-sm">
            <p>ارسال‌ها: <b>{{ toPersianDigits(d.dispatches.length) }}</b></p>
            <p>پیگیری‌ها: <b>{{ toPersianDigits(d.followups.length) }}</b></p>
            <p v-if="d.next_followup_date">پیگیری بعدی: <b>{{ fmtDate(d.next_followup_date) }}</b></p>
            <p v-if="d.followup_overdue" class="font-medium text-destructive">پیگیری عقب‌افتاده دارد.</p>
            <p v-if="d.feedback">بازخورد نهایی: <RequestSampleStatusBadge :status="d.feedback.status" kind="feedback" /></p>
            <p v-if="d.conversion">تبدیل به فروش در {{ fmtStamp(d.conversion.converted_at) }}</p>
          </div>
          <h2 class="border-t pt-3 text-base font-semibold">آخرین رویدادها</h2>
          <ul class="space-y-2 text-sm">
            <li v-for="e in d.events.slice(-4).reverse()" :key="e.id" class="flex gap-2">
              <Icon :name="EVENT_META[e.action]?.icon ?? 'lucide:circle'" class="mt-0.5 size-4 shrink-0 text-muted-foreground" />
              <span>{{ EVENT_META[e.action]?.label ?? e.action }}<span class="block text-xs text-muted-foreground">{{ e.user_name }} · {{ e.at_display }}</span></span>
            </li>
          </ul>
        </Card>
      </div>

      <!-- CUSTOMER -->
      <Card v-show="tab === 'customer'" class="gap-3 p-5 shadow-none">
        <h2 class="text-base font-semibold">اطلاعات مشتری</h2>
        <dl class="grid gap-x-6 gap-y-3 text-sm sm:grid-cols-2 lg:grid-cols-3">
          <div v-for="r in customerRows" :key="r.label"><dt class="text-xs text-muted-foreground">{{ r.label }}</dt><dd dir="auto">{{ r.value || '—' }}</dd></div>
        </dl>
        <div v-if="d.customer.contacts?.length" class="border-t pt-3">
          <h3 class="mb-2 text-sm font-semibold">اشخاص رابط</h3>
          <div class="grid gap-2 sm:grid-cols-2">
            <div v-for="(c, i) in d.customer.contacts" :key="i" class="rounded-lg border p-3 text-sm">
              <p class="font-medium">{{ c.name || '—' }}<span v-if="c.position" class="ms-2 text-xs font-normal text-muted-foreground">{{ c.position }}</span></p>
              <p v-if="c.mobile || c.landline" class="text-xs text-muted-foreground" dir="ltr">{{ [c.mobile, c.landline].filter(Boolean).join(' · ') }}</p>
            </div>
          </div>
        </div>
      </Card>

      <!-- PRODUCTS -->
      <div v-show="tab === 'products'" class="space-y-3">
        <Card v-for="(it, i) in d.items" :key="it.id ?? i" class="gap-3 p-5 shadow-none">
          <div class="flex flex-wrap items-center justify-between gap-2">
            <h2 class="text-base font-semibold" dir="auto">{{ toPersianDigits(i + 1) }}. {{ it.product_name }}<span v-if="it.grade" class="font-normal text-muted-foreground"> · {{ it.grade }}</span></h2>
            <Badge variant="secondary" dir="ltr">{{ it.quantity }} {{ it.unit }} × {{ it.number_of_samples }}</Badge>
          </div>
          <dl class="grid gap-x-6 gap-y-2 text-sm sm:grid-cols-2">
            <div><dt class="text-xs text-muted-foreground">بسته‌بندی</dt><dd>{{ it.packaging || '—' }}</dd></div>
            <div class="sm:col-span-2"><dt class="text-xs text-muted-foreground">مشخصات فنی</dt><dd class="whitespace-pre-line">{{ it.specifications || '—' }}</dd></div>
          </dl>
        </Card>
      </div>

      <!-- SAMPLE REQUIREMENTS -->
      <Card v-show="tab === 'sample'" dir="rtl" class="gap-3 p-5 text-right shadow-none">
        <h2 class="text-base font-semibold">مشخصات نمونهٔ درخواستی</h2>
        <div class="overflow-x-auto">
          <Table>
            <TableHeader><TableRow><TableHead>محصول</TableHead><TableHead>گرید</TableHead><TableHead>مقدار</TableHead><TableHead>تعداد بسته</TableHead><TableHead>بسته‌بندی</TableHead></TableRow></TableHeader>
            <TableBody>
              <TableRow v-for="(it, i) in d.items" :key="i"><TableCell dir="rtl">{{ it.product_name }}</TableCell><TableCell dir="rtl">{{ it.grade || '—' }}</TableCell><TableCell dir="rtl">{{ it.quantity }} {{ it.unit }}</TableCell><TableCell>{{ toPersianDigits(it.number_of_samples) }}</TableCell><TableCell dir="rtl">{{ it.packaging || '—' }}</TableCell></TableRow>
            </TableBody>
          </Table>
        </div>
        <dl class="grid gap-x-6 gap-y-3 border-t pt-3 text-sm sm:grid-cols-2">
          <div><dt class="text-xs text-muted-foreground">تاریخ موردنیاز دریافت</dt><dd>{{ d.required_delivery_date ? fmtDate(d.required_delivery_date) : '—' }}</dd></div>
          <div><dt class="text-xs text-muted-foreground">هدف ارسال نمونه</dt><dd class="whitespace-pre-line">{{ d.purpose || '—' }}</dd></div>
          <div class="sm:col-span-2"><dt class="text-xs text-muted-foreground">الزامات فنی مشتری</dt><dd class="whitespace-pre-line">{{ d.technical_requirements || '—' }}</dd></div>
        </dl>
      </Card>

      <!-- SHIPPING & DISPATCH -->
      <div v-show="tab === 'shipping'" class="space-y-4">
        <Card class="gap-3 p-5 shadow-none">
          <h2 class="text-base font-semibold">اطلاعات تحویل (درخواست‌شده)</h2>
          <dl class="grid gap-x-6 gap-y-3 text-sm sm:grid-cols-2 lg:grid-cols-3">
            <div><dt class="text-xs text-muted-foreground">شمارهٔ حوالهٔ نمونه</dt><dd dir="ltr">{{ d.dispatch_ref_number || '—' }}</dd></div>
            <div><dt class="text-xs text-muted-foreground">روش تحویل</dt><dd>{{ d.delivery_method || '—' }}</dd></div>
            <div><dt class="text-xs text-muted-foreground">تحویل‌گیرنده</dt><dd>{{ d.recipient_name || '—' }}</dd></div>
            <div class="sm:col-span-2"><dt class="text-xs text-muted-foreground">نشانی</dt><dd class="whitespace-pre-line">{{ [d.country, d.city, d.delivery_address].filter(Boolean).join('، ') || '—' }}</dd></div>
            <div><dt class="text-xs text-muted-foreground">کد پستی</dt><dd dir="ltr">{{ d.postal_code || '—' }}</dd></div>
            <div class="sm:col-span-3"><dt class="text-xs text-muted-foreground">توضیحات ویژه</dt><dd class="whitespace-pre-line">{{ d.delivery_instructions || '—' }}</dd></div>
          </dl>
        </Card>
        <Card v-if="d.delivered_at" class="gap-3 p-5 shadow-none">
          <h2 class="text-base font-semibold">دریافت نمونه توسط مشتری</h2>
          <dl class="grid gap-x-6 gap-y-3 text-sm sm:grid-cols-3">
            <div><dt class="text-xs text-muted-foreground">تاریخ دریافت</dt><dd>{{ fmtDate(d.delivered_at) }}</dd></div>
            <div><dt class="text-xs text-muted-foreground">دریافت‌کننده</dt><dd>{{ d.delivery_received_by || '—' }}</dd></div>
            <div><dt class="text-xs text-muted-foreground">توضیحات</dt><dd class="whitespace-pre-line">{{ d.delivery_note || '—' }}</dd></div>
          </dl>
        </Card>
        <Card class="gap-3 p-5 shadow-none">
          <div class="flex items-center justify-between">
            <h2 class="text-base font-semibold">محموله‌های ارسال‌شده</h2>
            <Button v-if="a.can_dispatch" size="sm" class="gap-2" @click="dispatchOpen = true"><Icon name="lucide:plus" class="size-4" /> محمولهٔ جدید</Button>
          </div>
          <p v-if="!d.dispatches.length" class="py-6 text-center text-sm text-muted-foreground">هنوز محموله‌ای ثبت نشده است.</p>
          <div v-for="s in d.dispatches" :key="s.id" class="rounded-xl border p-4">
            <div class="flex flex-wrap items-center justify-between gap-2">
              <p class="font-medium"><Icon name="lucide:truck" class="ms-1 inline size-4 text-primary" /> حواله <span dir="ltr">{{ s.reference_number }}</span> · {{ fmtDate(s.dispatch_date) }}</p>
              <Button v-if="a.can_dispatch && !isClosed" variant="ghost" size="icon" class="size-7 text-destructive" title="حذف محموله" aria-label="حذف محموله" @click="removeDispatch(s.id)"><Icon name="lucide:trash-2" class="size-4" /></Button>
            </div>
            <dl class="mt-2 grid gap-x-6 gap-y-1 text-sm sm:grid-cols-2 lg:grid-cols-4">
              <div><dt class="text-xs text-muted-foreground">روش ارسال</dt><dd>{{ s.delivery_method || '—' }}</dd></div>
              <div><dt class="text-xs text-muted-foreground">حمل‌کننده</dt><dd>{{ s.carrier || '—' }}</dd></div>
              <div><dt class="text-xs text-muted-foreground">کد رهگیری</dt><dd dir="ltr">{{ s.tracking_number || '—' }}</dd></div>
              <div><dt class="text-xs text-muted-foreground">مقدار ارسال‌شده</dt><dd dir="ltr">{{ s.shipped_quantity ?? '—' }} {{ s.shipped_quantity !== null ? s.unit : '' }}</dd></div>
              <div><dt class="text-xs text-muted-foreground">تحویل‌گیرنده</dt><dd>{{ s.recipient_name || '—' }}</dd></div>
              <div class="sm:col-span-3"><dt class="text-xs text-muted-foreground">توضیحات</dt><dd class="whitespace-pre-line">{{ s.notes || '—' }}</dd></div>
            </dl>
            <p class="mt-2 text-[11px] text-muted-foreground">ثبت‌شده توسط {{ s.created_by_name || '—' }} · {{ fmtStamp(s.created_at) }}</p>
          </div>
        </Card>
      </div>

      <!-- FOLLOW-UPS (timeline) -->
      <Card v-show="tab === 'followups'" class="gap-4 p-5 shadow-none">
        <div class="flex items-center justify-between">
          <h2 class="text-base font-semibold">تاریخچهٔ پیگیری‌های مشتری</h2>
          <Button v-if="a.can_follow_up" size="sm" class="gap-2" @click="openFollowUp(null)"><Icon name="lucide:plus" class="size-4" /> پیگیری جدید</Button>
        </div>
        <p v-if="d.followup_overdue" class="rounded-lg border border-destructive/30 bg-destructive/5 p-2 text-sm font-medium text-destructive">تاریخ آخرین پیگیری برنامه‌ریزی‌شده گذشته است؛ پیگیری جدیدی ثبت کنید.</p>
        <p v-if="!d.followups.length" class="py-6 text-center text-sm text-muted-foreground">هنوز پیگیری ثبت نشده است.<template v-if="a.can_follow_up"> بعد از ارسال نمونه، تماس‌ها و مکاتبات را اینجا ثبت کنید.</template></p>
        <ol class="relative space-y-5 border-s ps-6">
          <li v-for="f in [...d.followups].reverse()" :key="f.id" class="relative">
            <span class="absolute -start-[2.15rem] grid size-7 place-items-center rounded-full border bg-background" :class="f.overdue && 'border-destructive text-destructive'">
              <Icon :name="METHOD_ICONS[f.method]" class="size-3.5" />
            </span>
            <div class="rounded-xl border p-4" :class="f.overdue && 'border-destructive/40'">
              <div class="flex flex-wrap items-center justify-between gap-2">
                <p class="text-sm font-semibold">{{ METHOD_LABELS[f.method] }} · {{ fmtDate(f.followup_date) }}<span v-if="f.contact_person" class="font-normal text-muted-foreground"> · با {{ f.contact_person }}</span></p>
                <div v-if="f.can_edit" class="flex gap-1">
                  <Button variant="ghost" size="icon" class="size-7" title="ویرایش" aria-label="ویرایش" @click="openFollowUp(f)"><Icon name="lucide:pencil" class="size-3.5" /></Button>
                  <Button variant="ghost" size="icon" class="size-7 text-destructive" title="حذف" aria-label="حذف" @click="removeFollowUp(f.id)"><Icon name="lucide:trash-2" class="size-3.5" /></Button>
                </div>
              </div>
              <p v-if="f.result" class="mt-2 whitespace-pre-line text-sm"><b>نتیجه: </b>{{ f.result }}</p>
              <p v-if="f.customer_response" class="mt-1 whitespace-pre-line text-sm"><b>پاسخ مشتری: </b>{{ f.customer_response }}</p>
              <p v-if="f.internal_notes" class="mt-1 whitespace-pre-line text-sm text-muted-foreground"><b>یادداشت داخلی: </b>{{ f.internal_notes }}</p>
              <div class="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-[11px] text-muted-foreground">
                <span v-if="f.next_followup_date" :class="f.overdue && 'font-semibold text-destructive'">پیگیری بعدی: {{ fmtDate(f.next_followup_date) }}<template v-if="f.overdue"> (عقب‌افتاده)</template></span>
                <span>مسئول: {{ f.responsible.name || '—' }}</span>
                <span>ثبت: {{ f.created_by_name || '—' }} · {{ fmtStamp(f.created_at) }}</span>
              </div>
            </div>
          </li>
        </ol>
      </Card>

      <!-- FINAL FEEDBACK -->
      <Card v-show="tab === 'feedback'" class="gap-4 p-5 shadow-none">
        <div class="flex items-center justify-between">
          <h2 class="text-base font-semibold">بازخورد نهایی مشتری</h2>
          <Button v-if="a.can_feedback" size="sm" class="gap-2" @click="feedbackOpen = true"><Icon name="lucide:message-circle-heart" class="size-4" /> {{ d.feedback ? 'ویرایش بازخورد' : 'ثبت بازخورد' }}</Button>
        </div>
        <p v-if="!d.feedback" class="py-6 text-center text-sm text-muted-foreground">بازخورد نهایی هنوز ثبت نشده است. پیگیری‌های روزمره در تب «پیگیری‌ها» ثبت می‌شود.</p>
        <template v-else>
          <div class="flex flex-wrap items-center gap-3"><RequestSampleStatusBadge :status="d.feedback.status" kind="feedback" /><span class="text-sm text-muted-foreground">تاریخ: {{ d.feedback.date ? fmtDate(d.feedback.date) : '—' }}</span></div>
          <dl class="grid gap-x-6 gap-y-3 text-sm sm:grid-cols-2">
            <div><dt class="text-xs text-muted-foreground">مشخصات فنی</dt><dd>{{ d.feedback.technical_acceptance === null ? 'نامشخص' : d.feedback.technical_acceptance ? 'مورد تأیید' : 'مورد تأیید نیست' }}</dd></div>
            <div><dt class="text-xs text-muted-foreground">ثبت‌کنندهٔ ارزیابی</dt><dd>{{ d.feedback.evaluated_by || '—' }}</dd></div>
            <div class="sm:col-span-2"><dt class="text-xs text-muted-foreground">ارزیابی از محصول</dt><dd class="whitespace-pre-line">{{ d.feedback.product_evaluation || '—' }}</dd></div>
            <div class="sm:col-span-2"><dt class="text-xs text-muted-foreground">توضیحات مشتری</dt><dd class="whitespace-pre-line">{{ d.feedback.customer_comments || '—' }}</dd></div>
            <div v-if="d.feedback.rejection_reason" class="sm:col-span-2"><dt class="text-xs text-muted-foreground">دلیل عدم تأیید</dt><dd class="whitespace-pre-line text-destructive">{{ d.feedback.rejection_reason }}</dd></div>
            <div class="sm:col-span-2"><dt class="text-xs text-muted-foreground">پیشنهادهای اصلاح</dt><dd class="whitespace-pre-line">{{ d.feedback.improvement_suggestions || '—' }}</dd></div>
          </dl>
          <p v-if="d.conversion" class="rounded-lg border border-green-300 bg-green-50 p-3 text-sm dark:bg-green-950/30">
            <b>تبدیل به فروش:</b> {{ fmtStamp(d.conversion.converted_at) }}<span v-if="d.conversion.note"> — {{ d.conversion.note }}</span>
            <NuxtLink v-if="d.conversion.sale_id" :to="`/crm/sales`" class="ms-2 underline">مشاهدهٔ فروش‌ها</NuxtLink>
          </p>
        </template>
      </Card>

      <!-- ATTACHMENTS -->
      <Card v-show="tab === 'files'" class="gap-3 p-5 shadow-none">
        <div class="flex items-center justify-between">
          <h2 class="text-base font-semibold">فایل‌های پیوست</h2>
          <Button v-if="a.can_attach" size="sm" variant="outline" class="gap-2" @click="fileInput?.click()"><Icon name="lucide:upload" class="size-4" /> بارگذاری</Button>
          <input ref="fileInput" type="file" class="hidden" accept=".pdf,.png,.jpg,.jpeg,.webp,.doc,.docx,.xls,.xlsx,.csv,.txt" @change="onUpload">
        </div>
        <p v-if="!d.files.length" class="py-6 text-center text-sm text-muted-foreground">فایلی پیوست نشده است.</p>
        <ul class="divide-y">
          <li v-for="f in d.files" :key="f.id" class="flex items-center justify-between gap-3 py-2 text-sm">
            <span class="flex min-w-0 items-center gap-2"><Icon name="lucide:paperclip" class="size-4 shrink-0 text-muted-foreground" /><span class="truncate" dir="auto">{{ f.name }}</span><Badge variant="secondary">{{ FILE_KIND_LABELS[f.kind] ?? f.kind }}</Badge></span>
            <span class="flex shrink-0 items-center gap-1">
              <span class="text-xs text-muted-foreground" dir="ltr">{{ Math.max(1, Math.round(f.size / 1024)) }} KB</span>
              <Button variant="ghost" size="icon" class="size-7" title="دانلود" aria-label="دانلود" @click="store.downloadFile(f)"><Icon name="lucide:download" class="size-4" /></Button>
              <Button v-if="a.can_attach" variant="ghost" size="icon" class="size-7 text-destructive" title="حذف" aria-label="حذف" @click="removeFile(f.id)"><Icon name="lucide:trash-2" class="size-4" /></Button>
            </span>
          </li>
        </ul>
      </Card>

      <!-- ACTIVITY TIMELINE -->
      <Card v-show="tab === 'timeline'" class="gap-4 p-5 shadow-none">
        <h2 class="text-base font-semibold">تاریخچهٔ رویدادها (Activity Timeline)</h2>
        <ol class="relative space-y-4 border-s ps-6">
          <li v-for="e in [...d.events].reverse()" :key="e.id" class="relative">
            <span class="absolute -start-[2.15rem] grid size-7 place-items-center rounded-full border bg-background"><Icon :name="EVENT_META[e.action]?.icon ?? 'lucide:circle'" class="size-3.5 text-primary" /></span>
            <p class="text-sm font-medium">{{ EVENT_META[e.action]?.label ?? e.action }}
              <template v-if="e.from_status && e.to_status && e.from_status !== e.to_status">
                <span class="mx-1 text-xs font-normal text-muted-foreground">({{ STATUS_META[e.from_status]?.label }} ← {{ STATUS_META[e.to_status]?.label }})</span>
              </template>
            </p>
            <p v-if="e.note" class="whitespace-pre-line text-sm text-muted-foreground" dir="auto">{{ e.note }}</p>
            <p class="text-[11px] text-muted-foreground">{{ e.user_name || 'سیستم' }} · {{ e.at_display }}</p>
          </li>
        </ol>
      </Card>

      <!-- dialogs -->
      <RequestSampleReasonDialog
        v-model:open="reasonOpen" :title="reasonCfg.title" :description="reasonCfg.description" :label="reasonCfg.label"
        :required="reasonCfg.required" :confirm-label="reasonCfg.confirm" :tone="reasonCfg.tone" :saving="busy" @confirm="runReason"
      />
      <RequestSampleDispatchDialog
        v-model:open="dispatchOpen" :request-id="d.id" :saving="busy"
        :defaults="{ reference: d.dispatch_ref_number, recipient: d.recipient_name, method: d.delivery_method }" @submit="saveDispatch"
      />
      <RequestSampleDeliveryDialog
        v-model:open="deliveryOpen" :saving="busy" :defaults="{ receivedBy: d.recipient_name }" @submit="saveDelivery"
      />
      <RequestSampleFollowUpDialog
        v-model:open="followOpen" :request-id="d.id" :editing="editingFollow" :saving="busy" :reps="reps"
        :contacts="(d.customer.contacts ?? []).map(c => c.name).filter(Boolean)" @submit="saveFollowUp"
      />
      <RequestSampleFeedbackDialog v-model:open="feedbackOpen" :request-id="d.id" :current="d.feedback" :saving="busy" @submit="saveFeedback" />
      <LazyRequestSampleFormWizard v-if="wizardLoaded" v-model:open="wizardOpen" :request-id="d.id" @saved="onEdited" />
    </template>
  </ContainerWrapper>
</template>

<script setup lang="ts">
import type { SampleDetail, SampleFollowUp, SampleStatus } from '~/utils/requestSample'
import { EVENT_META, FILE_KIND_LABELS, METHOD_ICONS, METHOD_LABELS, PRIORITY_META, STATUS_META } from '~/utils/requestSample'
import { formatJalali, toPersianDigits } from '~/utils/jalali'
import { requestErrorMessage } from '~/utils/request-workflow'

const route = useRoute()
const store = useRequestSampleStore()
const notify = useNotify()
const { confirm } = useConfirm()
const id = computed(() => Number(route.params.id))

const d = ref<SampleDetail | null>(null)
const loading = ref(true)
const error = ref('')
const busy = ref(false)
const reps = ref<{ id: number, name: string }[]>([])
const a = computed(() => d.value!.my_actions)
const isClosed = computed(() => ['REJECTED', 'COMPLETED', 'CONVERTED', 'CANCELLED'].includes(d.value?.status ?? ''))

usePageSeoMeta({ title: computed(() => (d.value ? `درخواست نمونه ${d.value.code}` : 'درخواست نمونه')) })

async function load() {
  loading.value = true
  error.value = ''
  try { d.value = await store.get(id.value) }
  catch (e) { error.value = requestErrorMessage(e, 'این درخواست پیدا نشد یا اجازهٔ دیدن آن را ندارید.') }
  finally { loading.value = false }
}
onMounted(() => { load(); store.loadReps().then(r => (reps.value = r)).catch(() => {}) })
watch(id, load)

const fmtDate = (iso: string) => toPersianDigits(formatJalali(iso))
const fmtStamp = (iso: string | null) => {
  if (!iso) return '—'
  const t = new Date(iso)
  const day = t.toLocaleDateString('en-CA', { timeZone: 'Asia/Tehran' })
  const hm = t.toLocaleTimeString('en-GB', { timeZone: 'Asia/Tehran', hour: '2-digit', minute: '2-digit' })
  return toPersianDigits(`${formatJalali(day)} ${hm}`)
}

/* progress */
const FLOW = [
  { key: 'DRAFT', label: 'پیش‌نویس' }, { key: 'PENDING_APPROVAL', label: 'بررسی مدیر' }, { key: 'APPROVED', label: 'تأیید' },
  { key: 'DISPATCHED', label: 'ارسال‌شده' }, { key: 'AWAITING_FEEDBACK', label: 'تحویل و پیگیری' }, { key: 'DONE', label: 'پایان' },
]
const offFlow = computed(() => ['REJECTED', 'ON_HOLD', 'CANCELLED'].includes(d.value?.status ?? ''))
const flowIndex = computed(() => {
  const s = d.value?.status as SampleStatus
  const map: Record<string, number> = { DRAFT: 0, NEW_REQUEST: 1, PENDING_APPROVAL: 1, ON_HOLD: 1, REJECTED: 1, APPROVED: 2, DISPATCHED: 3, AWAITING_FEEDBACK: 4, COMPLETED: 5, CONVERTED: 5, CANCELLED: 1 }
  return map[s] ?? 0
})

/* tabs */
const tab = ref<string>((route.query.tab as string) || 'overview')
const setTab = (k: string) => { tab.value = k; navigateTo({ query: { ...route.query, tab: k } }, { replace: true }) }
const TABS = computed(() => [
  { key: 'overview', label: 'نمای کلی' }, { key: 'customer', label: 'مشتری' },
  { key: 'products', label: 'محصولات', count: d.value?.items.length },
  { key: 'sample', label: 'مشخصات نمونه' },
  { key: 'shipping', label: 'ارسال', count: d.value?.dispatches.length },
  { key: 'followups', label: 'پیگیری‌ها', count: d.value?.followups.length },
  { key: 'feedback', label: 'بازخورد مشتری' },
  { key: 'files', label: 'پیوست‌ها', count: d.value?.files.length },
  { key: 'timeline', label: 'تاریخچه' },
])

const overviewRows = computed(() => {
  const x = d.value!
  return [
    { label: 'مشتری', value: x.customer.name }, { label: 'کارشناس فروش', value: x.sales_rep.name ?? '' },
    { label: 'اولویت', value: PRIORITY_META[x.priority]?.label ?? '' }, { label: 'شمارهٔ حوالهٔ نمونه', value: x.dispatch_ref_number ?? '' },
    { label: 'محصولات', value: x.items.map(i => `${i.product_name}${i.grade ? ` · ${i.grade}` : ''} — ${i.quantity} ${i.unit} × ${i.number_of_samples}`).join('\n'), wide: true },
    { label: 'هدف ارسال نمونه', value: x.purpose ?? '' }, { label: 'تاریخ موردنیاز', value: x.required_delivery_date ? fmtDate(x.required_delivery_date) : '' },
    { label: 'ثبت نهایی در', value: x.submitted_at ? fmtStamp(x.submitted_at) : '' },
    { label: 'یادداشت داخلی', value: x.internal_notes ?? '', wide: true },
  ]
})
const customerRows = computed(() => {
  const c = d.value!.customer
  return [
    { label: 'نام', value: c.name }, { label: 'نام شرکت', value: c.company_name ?? '' }, { label: 'برند', value: c.brand ?? '' },
    { label: 'نوع', value: c.customer_type === 'LEGAL' ? 'حقوقی' : c.customer_type === 'INDIVIDUAL' ? 'حقیقی' : '' },
    { label: 'تلفن شرکت', value: c.company_phone ?? '' }, { label: 'استان / شهر', value: [c.province, c.city].filter(Boolean).join('، ') },
    { label: 'صنعت', value: c.category ?? '' },
  ]
})

/* workflow */
async function apply(fn: () => Promise<SampleDetail>, okMsg: string) {
  busy.value = true
  try { d.value = await fn(); notify.success(okMsg); return true }
  catch (e) { notify.error(requestErrorMessage(e, 'عملیات انجام نشد.')); return false }
  finally { busy.value = false }
}
const doSubmit = () => apply(() => store.transition(id.value, 'submit'), 'درخواست ثبت و برای تأیید ارسال شد.')

const reasonOpen = ref(false)
const reasonAction = ref('')
const REASONS: Record<string, { title: string, description?: string, label: string, required: boolean, confirm: string, tone: 'danger' | 'default', ok: string }> = {
  approve: { title: 'تأیید درخواست', description: 'پس از تأیید، ثبت اطلاعات ارسال فعال می‌شود و یادآوری روزانهٔ ارسال برای کارشناس مسئول شروع می‌شود.', label: 'توضیحات (اختیاری)', required: false, confirm: 'تأیید درخواست', tone: 'default', ok: 'درخواست تأیید شد.' },
  reject: { title: 'رد درخواست', description: 'دلیل رد برای ثبت‌کننده نمایش داده می‌شود.', label: 'دلیل رد', required: true, confirm: 'رد درخواست', tone: 'danger', ok: 'درخواست رد شد.' },
  hold: { title: 'توقف موقت درخواست', label: 'دلیل توقف', required: true, confirm: 'توقف', tone: 'default', ok: 'درخواست متوقف شد.' },
  resume: { title: 'ازسرگیری درخواست', description: 'درخواست دوباره به صف بررسی برمی‌گردد.', label: 'توضیحات (اختیاری)', required: false, confirm: 'ازسرگیری', tone: 'default', ok: 'درخواست ازسر گرفته شد.' },
  complete: { title: 'تکمیل درخواست', description: 'نمونه مورد تأیید مشتری بوده است.', label: 'توضیحات (اختیاری)', required: false, confirm: 'تکمیل', tone: 'default', ok: 'درخواست تکمیل شد.' },
  convert: { title: 'تبدیل به فروش', description: 'نمونهٔ تأییدشده به خرید یا فرصت فروش تبدیل شد.', label: 'توضیحات (مثلاً شمارهٔ سفارش)', required: false, confirm: 'ثبت تبدیل', tone: 'default', ok: 'درخواست به فروش تبدیل شد.' },
  cancel: { title: 'لغو درخواست', label: 'دلیل لغو', required: true, confirm: 'لغو درخواست', tone: 'danger', ok: 'درخواست لغو شد.' },
}
const reasonCfg = computed(() => REASONS[reasonAction.value] ?? REASONS.approve!)
function openReason(action: string) { reasonAction.value = action; reasonOpen.value = true }
async function runReason(note: string) {
  const act = reasonAction.value
  const ok = await apply(
    () => (act === 'convert' ? store.convert(id.value, note, null) : store.transition(id.value, act, note)),
    REASONS[act]!.ok,
  )
  if (ok) reasonOpen.value = false
}

/* dispatch / follow-ups / feedback */
const dispatchOpen = ref(false)
async function saveDispatch(body: Record<string, unknown>) {
  if (await apply(() => store.addDispatch(id.value, body), 'ارسال نمونه ثبت شد.')) { dispatchOpen.value = false; setTab('shipping') }
}
async function removeDispatch(did: number) {
  if (!(await confirm({ title: 'حذف محموله', description: 'این محموله حذف شود؟', confirmLabel: 'حذف', tone: 'danger' }))) return
  await apply(() => store.deleteDispatch(id.value, did), 'محموله حذف شد.')
}
const deliveryOpen = ref(false)
async function saveDelivery(body: Record<string, unknown>) {
  if (await apply(() => store.confirmDelivery(id.value, body), 'دریافت نمونه توسط مشتری ثبت شد.')) { deliveryOpen.value = false; setTab('followups') }
}
const followOpen = ref(false)
const editingFollow = ref<SampleFollowUp | null>(null)
function openFollowUp(f: SampleFollowUp | null) { editingFollow.value = f; followOpen.value = true }
async function saveFollowUp(body: Record<string, unknown>) {
  const f = editingFollow.value
  const ok = await apply(() => (f ? store.updateFollowUp(id.value, f.id, body) : store.addFollowUp(id.value, body)), f ? 'پیگیری ویرایش شد.' : 'پیگیری ثبت شد.')
  if (ok) { followOpen.value = false; setTab('followups') }
}
async function removeFollowUp(fid: number) {
  if (!(await confirm({ title: 'حذف پیگیری', description: 'این پیگیری حذف شود؟', confirmLabel: 'حذف', tone: 'danger' }))) return
  await apply(() => store.deleteFollowUp(id.value, fid), 'پیگیری حذف شد.')
}
const feedbackOpen = ref(false)
async function saveFeedback(body: Record<string, unknown>) {
  if (await apply(() => store.setFeedback(id.value, body), 'بازخورد نهایی ثبت شد.')) { feedbackOpen.value = false; setTab('feedback') }
}

/* new linked request / delete / edit / files */
async function newRequest() {
  try {
    const n = await store.newRequestFrom(id.value)
    notify.success('پیش‌نویس درخواست جدید ساخته شد؛ شمارهٔ حوالهٔ جدید را وارد کنید.')
    await navigateTo(`/crm/request-samples/${n.id}`)
  }
  catch (e) { notify.error(requestErrorMessage(e, 'ایجاد درخواست جدید انجام نشد.')) }
}
async function askDelete() {
  if (!(await confirm({ title: 'حذف درخواست', description: `درخواست ${d.value!.code} حذف شود؟`, confirmLabel: 'حذف', tone: 'danger' }))) return
  try { await store.remove(id.value); notify.success('درخواست حذف شد.'); await navigateTo('/crm/request-samples') }
  catch (e) { notify.error(requestErrorMessage(e, 'حذف انجام نشد.')) }
}
const wizardOpen = ref(false)
const wizardLoaded = ref(false)
watch(wizardOpen, (v) => { if (v) wizardLoaded.value = true })
async function onEdited(_id: number, submitted: boolean) {
  notify.success(submitted ? 'درخواست ثبت شد.' : 'تغییرات ذخیره شد.')
  await load()
}
const fileInput = ref<HTMLInputElement | null>(null)
async function onUpload(ev: Event) {
  const el = ev.target as HTMLInputElement
  const file = el.files?.[0]
  el.value = ''
  if (!file) return
  try { await store.uploadFile(file, 'OTHER', id.value); notify.success('فایل بارگذاری شد.'); await load() }
  catch (e) { notify.error(requestErrorMessage(e, 'بارگذاری فایل انجام نشد.')) }
}
async function removeFile(fid: string) {
  if (!(await confirm({ title: 'حذف فایل', description: 'این فایل حذف شود؟', confirmLabel: 'حذف', tone: 'danger' }))) return
  try { await store.deleteFile(fid); await load() }
  catch (e) { notify.error(requestErrorMessage(e, 'حذف فایل انجام نشد.')) }
}
</script>
