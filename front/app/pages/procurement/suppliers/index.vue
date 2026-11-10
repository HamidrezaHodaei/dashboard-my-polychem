<template>
  <ContainerWrapper
    class="space-y-6 py-6 md:py-8"
  >
    <AccessPageHeader
      title="تأمین‌کنندگان"
      description="تأمین‌کنندگان ثبت‌نام‌شده در فرم عمومی را بررسی کنید یا مورد جدیدی اضافه کنید."
      action-label="افزودن تأمین‌کننده"
      @action="openCreate"
    >
    <template #actions>
      <ExportButtons
        v-if="store.canExport"
        :busy="exporting"
        :disabled="!store.total"
        @export="runExport"
      />
    </template>
    </AccessPageHeader>

    <div class="grid gap-4 sm:grid-cols-4">
      <AccessStat
        label="تعداد کل تأمین‌کنندگان"
        :value="store.total"
        icon="lucide:truck"
      />
      <AccessStat
        label="فعال"
        :value="countByStatus('ACTIVE')"
        icon="lucide:badge-check"
      />
      <AccessStat
        label="نیمه‌فعال"
        :value="countByStatus('SEMI_ACTIVE')"
        icon="lucide:timer"
      />
      <AccessStat
        label="غیرفعال"
        :value="countByStatus('INACTIVE')"
        icon="lucide:ban"
      />
    </div>

    <Card class="overflow-hidden py-0 shadow-none">
      <div class="flex min-w-0 flex-col gap-3 border-b p-4">
        <div class="grid w-full min-w-0 gap-3 sm:grid-cols-2 xl:grid-cols-5">
          <div class="relative w-full min-w-0">
            <Icon
              name="lucide:search"
              class="absolute right-3 top-2.5 size-4 text-muted-foreground"
            />
            <Input
              v-model="store.filters.search"
              dir="rtl"
              placeholder="جستجوی تأمین‌کننده، برند یا مغازه، نام کالا، شناسه یا کد پستی..."
              class="w-full min-w-0 pr-9 text-right"
              @keyup.enter="applyNow"
            />
          </div>
          <Select v-model="categoryModel">
            <SelectTrigger class="w-full">
              <SelectValue placeholder="دسته‌بندی" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">
                همه دسته‌بندی‌ها
              </SelectItem>
              <SelectItem
                v-for="c in store.categories"
                :key="c"
                :value="c"
              >
                {{ c }}
              </SelectItem>
            </SelectContent>
          </Select>
          <Select
            v-if="subcategoryOptions.length"
            v-model="subcategoryModel"
          >
            <SelectTrigger class="w-full">
              <SelectValue placeholder="دسته‌بندی فرعی" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">
                همه دسته‌بندی‌های فرعی
              </SelectItem>
              <SelectItem
                v-for="c in subcategoryOptions"
                :key="c.id"
                :value="String(c.id)"
              >
                {{ c.label }}
              </SelectItem>
            </SelectContent>
          </Select>
          <Select v-model="statusModel">
            <SelectTrigger class="w-full">
              <SelectValue placeholder="وضعیت" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">
                همه وضعیت‌ها
              </SelectItem>
              <SelectItem value="ACTIVE">
                فعال
              </SelectItem>
              <SelectItem value="SEMI_ACTIVE">
                نیمه‌فعال
              </SelectItem>
              <SelectItem value="INACTIVE">
                غیرفعال
              </SelectItem>
            </SelectContent>
          </Select>
          <Select v-model="qualityModel">
            <SelectTrigger class="w-full xl:min-w-48">
              <SelectValue placeholder="کیفیت" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">
                همه سطح‌های کیفیت
              </SelectItem>
              <SelectItem value="EXCELLENT">
                عالی
              </SelectItem>
              <SelectItem value="MEDIUM">
                متوسط
              </SelectItem>
              <SelectItem value="WEAK">
                ضعیف
              </SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div class="flex flex-wrap items-center justify-start gap-2">
          <Button
            variant="ghost"
            @click="resetAll"
          >
            بازنشانی
          </Button>
          <Button
            v-if="store.canUpdate"
            variant="outline"
            class="gap-2"
            @click="categoriesOpen = true"
          >
            <Icon
              name="lucide:tags"
              class="size-4"
            /> دسته‌بندی‌ها
          </Button>
          <span
            v-if="store.loading && store.suppliers.length"
            class="flex items-center gap-1.5 text-xs text-muted-foreground"
          >
            <Icon
              name="lucide:loader-circle"
              class="size-3.5 animate-spin"
            /> در حال جستجو...
          </span>
        </div>
      </div>

      <div class="overflow-x-auto">
        <div
          v-if="store.loading && !store.suppliers.length"
          class="p-8 text-center text-sm text-muted-foreground"
        >
          در حال بارگذاری تأمین‌کنندگان...
        </div>
        <div
          v-else-if="store.loadError"
          class="p-8 text-center text-sm text-destructive"
        >
          {{ store.loadError }}
        </div>
        <Table v-else-if="store.suppliers.length">
          <TableHeader>
            <TableRow>
              <TableHead>تأمین‌کننده</TableHead>
              <TableHead>دسته‌بندی</TableHead>
              <TableHead>راه ارتباطی</TableHead>
              <TableHead>منبع ثبت</TableHead>
              <TableHead>وضعیت درخواست</TableHead>
              <TableHead>وضعیت</TableHead>
              <TableHead>کیفیت</TableHead>
              <TableHead class="text-right">
                عملیات
              </TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            <TableRow
              v-for="s in store.suppliers"
              :key="s.id"
               class="border-b border-slate-300/70 transition-colors odd:bg-white even:bg-slate-100 hover:bg-amber-100/70 dark:border-zinc-700 odd:bg-white even:bg-slate-100 dark:odd:bg-zinc-900 dark:even:bg-zinc-800 dark:hover:bg-amber-300/15"
            >
              <TableCell>
                <!-- نام تأمین‌کننده + نام برند یا مغازه (شخص حقیقی) در یک خط -->
                <p
                  class="font-medium"
                  dir="auto"
                >
                  {{ supplierTitle(s) }}
                </p>
                <p class="text-xs text-muted-foreground">
                  {{ s.supplier_type === 'LEGAL' ? 'شخص حقوقی' : 'شخص حقیقی' }}
                </p>
                <!-- Products that match the search text -->
                <div
                  v-if="matchedProducts(s).length"
                  class="mt-1 flex flex-wrap gap-1"
                >
                  <Badge
                    v-for="(p, i) in matchedProducts(s)"
                    :key="i"
                    variant="secondary"
                    class="gap-1 font-normal"
                    dir="auto"
                  >
                    <Icon
                      name="lucide:package"
                      class="size-3"
                    />
                    {{ p.name }}
                  </Badge>
                </div>
              </TableCell>
              <TableCell>
                <Badge
                  v-if="s.category"
                  variant="outline"
                  dir="auto"
                >
                  {{ s.category }}
                </Badge>
                <span
                  v-else
                  class="text-xs text-muted-foreground"
                >—</span>
                <p
                  v-if="s.subcategory"
                  class="mt-1 text-xs text-muted-foreground"
                  dir="auto"
                >
                  {{ s.subcategory }}
                </p>
              </TableCell>
              <TableCell class="text-sm">
                <!-- Primary contact person (first in the list) -->
                <template v-if="s.contacts?.length">
                  <p dir="auto">
                    {{ contactName(s.contacts[0]) }}
                    <span class="text-xs text-muted-foreground">· {{ s.contacts[0].position }}</span>
                  </p>
                  <p
                    v-if="primaryNumber(s.contacts[0])"
                    class="text-xs text-muted-foreground"
                    dir="ltr"
                  >
                    {{ primaryNumber(s.contacts[0]) }}
                  </p>
                  <p
                    v-if="s.contacts.length > 1"
                    class="text-xs text-muted-foreground"
                  >
                    و {{ s.contacts.length - 1 }} نفر دیگر
                  </p>
                </template>
                <!-- Older records without contact persons -->
                <template v-else>
                  <p v-if="s.email">
                    {{ s.email }}
                  </p>
                  <p
                    v-if="s.phones[0]"
                    class="text-xs text-muted-foreground"
                    dir="ltr"
                  >
                    {{ s.phones[0].number }}
                  </p>
                </template>
              </TableCell>
              <TableCell>
                <Badge :variant="s.is_public_submission ? 'secondary' : 'outline'">
                  {{ s.is_public_submission ? 'فرم عمومی' : 'ثبت توسط کارمند' }}
                </Badge>
                <p
                  v-if="!s.is_public_submission && s.created_by_name"
                  class="mt-1 text-xs text-muted-foreground"
                  dir="auto"
                >
                  {{ s.created_by_name }}
                </p>
              </TableCell>
              <TableCell>
                <RequestStatusBadge
                  :status="s.review_status"
                  :draft="!s.is_finalized"
                  :change-requested="!!s.change_request_note"
                />
                <p
                  v-if="s.review_note && (s.review_status === 'NEEDS_EDIT' || s.review_status === 'REJECTED')"
                  class="mt-1 max-w-48 truncate text-xs text-muted-foreground"
                  dir="auto"
                  :title="s.review_note"
                >
                  {{ s.review_note }}
                </p>
              </TableCell>
              <TableCell>
                <Select
                  :model-value="s.status"
                  :disabled="!store.canUpdate"
                  @update:model-value="v => setStatus(s, v as SupplierStatus)"
                >
                  <SelectTrigger class="h-8 w-36">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="ACTIVE">
                      فعال
                    </SelectItem>
                    <SelectItem value="SEMI_ACTIVE">
                      نیمه‌فعال
                    </SelectItem>
                    <SelectItem value="INACTIVE">
                      غیرفعال
                    </SelectItem>
                  </SelectContent>
                </Select>
              </TableCell>
              <TableCell>
                <Select
                  :model-value="s.quality ?? 'NONE'"
                  :disabled="!store.canUpdate"
                  @update:model-value="v => setQuality(s, v === 'NONE' ? null : v as SupplierQuality)"
                >
                  <SelectTrigger class="h-8 w-44">
                    <SelectValue placeholder="ارزیابی‌نشده" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="NONE">
                      ارزیابی‌نشده
                    </SelectItem>
                    <SelectItem value="EXCELLENT">
                      عالی
                    </SelectItem>
                    <SelectItem value="MEDIUM">
                      متوسط
                    </SelectItem>
                    <SelectItem value="WEAK">
                      ضعیف
                    </SelectItem>
                  </SelectContent>
                </Select>
              </TableCell>
              <TableCell class="text-right">
                <div class="flex justify-end gap-1">
                  <Button
                    variant="ghost"
                    size="icon"
                    title="مشاهده جزئیات"
                    aria-label="مشاهده جزئیات"
                    @click="openView(s)"
                  >
                    <Icon
                      name="lucide:eye"
                      class="size-4"
                    />
                  </Button>
                  <Button
                    v-if="s.my_actions?.can_review && requestReviewActionsFor(s.review_status).length"
                    variant="ghost"
                    size="icon"
                    title="بررسی درخواست"
                    aria-label="بررسی درخواست"
                    @click="openReview(s)"
                  >
                    <Icon
                      name="lucide:shield-check"
                      class="size-4"
                    />
                  </Button>
                  <Button
                    v-if="s.my_actions?.can_finalize"
                    variant="ghost"
                    size="icon"
                    :title="s.review_status === 'NEEDS_EDIT' ? 'ثبت مجدد (ارسال برای بررسی)' : 'ثبت نهایی'"
                    :aria-label="s.review_status === 'NEEDS_EDIT' ? 'ثبت مجدد' : 'ثبت نهایی'"
                    @click="finalizeRow(s)"
                  >
                    <Icon
                      name="lucide:send"
                      class="size-4"
                    />
                  </Button>
                  <Button
                    v-if="s.my_actions?.can_request_change"
                    variant="ghost"
                    size="icon"
                    title="درخواست تغییر اطلاعات"
                    aria-label="درخواست تغییر اطلاعات"
                    @click="openChangeRequest(s)"
                  >
                    <Icon
                      name="lucide:file-pen-line"
                      class="size-4"
                    />
                  </Button>
                  <Button
                    v-if="s.my_actions?.can_edit"
                    variant="ghost"
                    size="icon"
                    title="ویرایش"
                    aria-label="ویرایش"
                    @click="openEdit(s)"
                  >
                    <Icon
                      name="lucide:pencil"
                      class="size-4"
                    />
                  </Button>
                  <Button
                    v-if="store.canDelete"
                    variant="ghost"
                    size="icon"
                    class="text-destructive"
                    title="حذف"
                    aria-label="حذف"
                    @click="confirmDelete(s)"
                  >
                    <Icon
                      name="lucide:trash-2"
                      class="size-4"
                    />
                  </Button>
                </div>
              </TableCell>
            </TableRow>
          </TableBody>
        </Table>
        <div
          v-else
          class="p-8 text-center text-sm text-muted-foreground"
        >
          تأمین‌کننده‌ای با این فیلترها پیدا نشد.
        </div>
      </div>

      <NumberedPagination
        :page="store.page"
        :page-size="store.perPage"
        :total="store.total"
        :loading="store.loading"
        @update:page="store.setPage"
      />
    </Card>

    <!-- View details -->
    <Dialog v-model:open="viewOpen">
      <DialogContent class="fixed !inset-0 !left-0 !top-0 !h-dvh !max-h-none !w-screen !max-w-none !translate-x-0 !translate-y-0 flex flex-col gap-0 overflow-hidden !rounded-none border-0 p-0 sm:!max-w-none">
        <DialogHeader class="border-b px-6 py-4 text-right">
          <div class="flex flex-wrap items-center gap-2">
            <DialogTitle
              class="text-lg font-semibold"
              dir="auto"
            >
              {{ viewing?.display_name }}
            </DialogTitle>
            <Badge variant="outline">
              {{ viewing?.supplier_type === 'LEGAL' ? 'شخص حقوقی' : 'شخص حقیقی' }}
            </Badge>
            <Badge :variant="viewing?.status === 'ACTIVE' ? 'default' : 'secondary'">
              {{ statusLabel[viewing?.status ?? 'SEMI_ACTIVE'] }}
            </Badge>
            <RequestStatusBadge
              v-if="viewing"
              :status="viewing.review_status"
              :draft="!viewing.is_finalized"
              :change-requested="!!viewing.change_request_note"
            />
            <Badge
              v-if="viewing?.quality"
              variant="outline"
            >
              {{ qualityLabel[viewing.quality] }}
            </Badge>
          </div>
          <DialogDescription>
            {{ viewing?.is_public_submission ? 'از طریق فرم عمومی ثبت تأمین‌کننده ارسال شده است.' : viewing?.created_by_name ? `ثبت‌شده توسط ${viewing.created_by_name}.` : 'مستقیماً توسط کارمند ثبت شده است.' }}
          </DialogDescription>
        </DialogHeader>

        <RequestBanner
          v-if="viewing"
          class="px-6 pt-4"
          :status="viewing.review_status"
          :note="viewing.review_note"
          :change-request-note="viewing.change_request_note"
        />
        <DetailNav :watch-key="viewing?.id" />
        <div
          v-if="viewing"
          class="detail-body flex-1 overflow-y-auto bg-muted/20 px-6 py-6 text-sm"
        >
          <section class="space-y-3">
            <h3 class="font-semibold">
              اطلاعات هویتی
            </h3>
            <dl class="grid gap-x-6 gap-y-3 sm:grid-cols-2">
              <template v-if="viewing.supplier_type === 'LEGAL'">
                <div
                  v-for="r in legalRows"
                  :key="r.label"
                >
                  <dt class="text-xs text-muted-foreground">
                    {{ r.label }}
                  </dt>
                  <dd dir="auto">
                    {{ r.value || '—' }}
                  </dd>
                </div>
              </template>
              <template v-else>
                <div
                  v-for="r in individualRows"
                  :key="r.label"
                >
                  <dt class="text-xs text-muted-foreground">
                    {{ r.label }}
                  </dt>
                  <dd dir="auto">
                    {{ r.value || '—' }}
                  </dd>
                </div>
              </template>
            </dl>
          </section>

          <section class="space-y-3">
            <h3 class="font-semibold">
              اطلاعات تماس
            </h3>
            <dl class="grid gap-x-6 gap-y-3 sm:grid-cols-2">
              <div>
                <dt class="text-xs text-muted-foreground">
                  ایمیل
                </dt>
                <dd
                  dir="ltr"
                  class="text-left"
                >
                  {{ viewing.email || '—' }}
                </dd>
              </div>
              <div>
                <dt class="text-xs text-muted-foreground">
                  وب‌سایت
                </dt>
                <dd
                  dir="ltr"
                  class="text-left"
                >
                  {{ viewing.website || '—' }}
                </dd>
              </div>
              <div>
                <dt class="text-xs text-muted-foreground">
                  کد پستی
                </dt>
                <dd
                  dir="ltr"
                  class="text-left"
                >
                  {{ viewing.postal_code || '—' }}
                </dd>
              </div>
              <div class="sm:col-span-2">
                <dt class="text-xs text-muted-foreground">
                  نشانی
                </dt>
                <dd dir="auto">
                  {{ viewing.address || '—' }}
                </dd>
              </div>
            </dl>

            <!-- Contact persons -->
            <div
              v-if="viewing.contacts?.length"
              class="space-y-3 pt-1"
            >
              <p class="text-xs font-semibold text-muted-foreground">
                افراد تماس ({{ viewing.contacts.length }})
              </p>
              <div
                v-for="(c, i) in viewing.contacts"
                :key="i"
                class="rounded-xl border p-4"
              >
                <div class="flex flex-wrap items-center justify-between gap-2">
                  <p
                    class="font-medium"
                    dir="auto"
                  >
                    {{ contactName(c) }}
                  </p>
                  <Badge
                    variant="secondary"
                    class="font-normal"
                  >
                    {{ c.position }}
                  </Badge>
                </div>
                <dl class="mt-3 grid gap-x-6 gap-y-2 sm:grid-cols-3">
                  <div>
                    <dt class="text-xs text-muted-foreground">
                      ایمیل
                    </dt>
                    <dd
                      dir="ltr"
                      class="text-left"
                    >
                      {{ c.email || '—' }}
                    </dd>
                  </div>
                  <div>
                    <dt class="text-xs text-muted-foreground">
                      موبایل
                    </dt>
                    <dd
                      dir="ltr"
                      class="text-left"
                    >
                      {{ c.mobile || '—' }}
                    </dd>
                  </div>
                  <div>
                    <dt class="text-xs text-muted-foreground">
                      تلفن ثابت
                    </dt>
                    <dd
                      dir="ltr"
                      class="text-left"
                    >
                      {{ c.landline || '—' }}
                    </dd>
                  </div>
                </dl>
              </div>
            </div>

            <!-- Older records: flat phone list only -->
            <div
              v-else
              class="flex flex-wrap gap-2"
            >
              <Badge
                v-for="(p, i) in viewing.phones"
                :key="i"
                variant="outline"
                class="font-normal"
              >
                {{ p.type === 'mobile' ? 'موبایل' : 'تلفن ثابت' }}: <span dir="ltr">{{ p.number }}</span>
              </Badge>
            </div>
          </section>

          <section class="space-y-3">
            <h3 class="font-semibold">
              اطلاعات کسب‌وکار
            </h3>
            <dl class="grid gap-x-6 gap-y-3 sm:grid-cols-2">
              <div>
                <dt class="text-xs text-muted-foreground">
                  دسته‌بندی
                </dt>
                <dd dir="auto">
                  {{ viewing.category || '—' }}
                </dd>
              </div>
              <div>
                <dt class="text-xs text-muted-foreground">
                  دسته‌بندی فرعی
                </dt>
                <dd dir="auto">
                  {{ viewing.subcategory || '—' }}
                </dd>
              </div>
              <div>
                <dt class="text-xs text-muted-foreground">
                  ظرفیت تأمین
                </dt>
                <dd dir="auto">
                  {{ viewing.capacity || '—' }}
                </dd>
              </div>
              <div>
                <dt class="text-xs text-muted-foreground">
                  سابقه فعالیت
                </dt>
                <dd dir="auto">
                  {{ viewing.experience || '—' }}
                </dd>
              </div>
              <div class="sm:col-span-2">
                <dt class="mb-1 text-xs text-muted-foreground">
                  نوع فعالیت
                </dt>
                <dd class="flex flex-wrap gap-1.5">
                  <Badge
                    v-for="a in activityList"
                    :key="a"
                    variant="secondary"
                    class="font-normal"
                  >
                    {{ a }}
                  </Badge>
                  <span v-if="!activityList.length">—</span>
                </dd>
              </div>
            </dl>
          </section>

          <section class="space-y-3">
            <h3 class="font-semibold">
              کالاها و خدمات
              <span class="font-normal text-muted-foreground">({{ viewing.products.length }})</span>
            </h3>
            <p
              v-if="!viewing.products.length"
              class="text-muted-foreground"
            >
              موردی ثبت نشده است.
            </p>
            <div
              v-for="(p, i) in viewing.products"
              :key="i"
              class="rounded-xl border p-4"
            >
              <div class="flex flex-wrap items-center justify-between gap-2">
                <p
                  class="font-medium"
                  dir="auto"
                >
                  {{ p.name }}
                </p>
                <Badge
                  variant="outline"
                  class="font-normal"
                >
                  {{ paymentText(p) }}
                </Badge>
              </div>
              <dl class="mt-3 grid gap-x-6 gap-y-2 sm:grid-cols-2">
                <div>
                  <dt class="text-xs text-muted-foreground">
                    مشخصات
                  </dt>
                  <dd dir="auto">
                    {{ p.specs || '—' }}
                  </dd>
                </div>
                <div>
                  <dt class="text-xs text-muted-foreground">
                    تصویر کالا
                  </dt>
                  <dd
                    dir="ltr"
                    class="text-left"
                  >
                    <button
                      v-if="isFileRef(p.image)"
                      type="button"
                      class="inline-flex items-center gap-1.5 text-primary underline-offset-2 hover:underline"
                      @click="download(p.image)"
                    >
                      <Icon
                        name="lucide:download"
                        class="size-3.5"
                      />
                      {{ p.image.name }}
                    </button>
                    <template v-else>
                      —
                    </template>
                  </dd>
                </div>
                <div>
                  <dt class="text-xs text-muted-foreground">
                    برگه مشخصات
                  </dt>
                  <dd
                    dir="ltr"
                    class="text-left"
                  >
                    <button
                      v-if="isFileRef(p.datasheet)"
                      type="button"
                      class="inline-flex items-center gap-1.5 text-primary underline-offset-2 hover:underline"
                      @click="download(p.datasheet)"
                    >
                      <Icon
                        name="lucide:download"
                        class="size-3.5"
                      />
                      {{ p.datasheet.name }}
                    </button>
                    <template v-else>
                      {{ p.datasheet || '—' }}
                    </template>
                  </dd>
                </div>
                <div class="sm:col-span-2">
                  <dt class="text-xs text-muted-foreground">
                    توضیحات
                  </dt>
                  <dd dir="auto">
                    {{ p.description || '—' }}
                  </dd>
                </div>
              </dl>
            </div>
          </section>

          <section
            v-if="viewing.bank_accounts?.length"
            class="space-y-3"
          >
            <h3 class="font-semibold">
              حساب‌های بانکی
            </h3>
            <div class="grid gap-3 sm:grid-cols-2">
              <div
                v-for="(b, i) in viewing.bank_accounts"
                :key="i"
                class="space-y-2 rounded-xl border p-4"
              >
                <p
                  class="font-medium"
                  dir="auto"
                >
                  {{ b.holder_name || '—' }}
                  <span
                    v-if="b.bank_name"
                    class="text-xs font-normal text-muted-foreground"
                  >· {{ b.bank_name }}</span>
                </p>
                <dl class="space-y-1.5">
                  <div v-if="b.card_number">
                    <dt class="text-xs text-muted-foreground">
                      شماره کارت
                    </dt>
                    <dd
                      dir="ltr"
                      class="text-left"
                    >
                      {{ b.card_number.replace(/(\d{4})(?=\d)/g, '$1 ') }}
                    </dd>
                  </div>
                  <div v-if="b.account_number">
                    <dt class="text-xs text-muted-foreground">
                      شماره حساب
                    </dt>
                    <dd
                      dir="ltr"
                      class="text-left"
                    >
                      {{ b.account_number }}
                    </dd>
                  </div>
                  <div v-if="b.sheba">
                    <dt class="text-xs text-muted-foreground">
                      شماره شبا
                    </dt>
                    <dd
                      dir="ltr"
                      class="text-left"
                    >
                      {{ b.sheba }}
                    </dd>
                  </div>
                </dl>
              </div>
            </div>
          </section>

          <section
            v-if="viewing.catalog_files.length"
            class="space-y-3"
          >
            <h3 class="font-semibold">
              فایل‌های کاتالوگ
            </h3>
            <ul class="flex flex-wrap gap-2">
              <li
                v-for="(f, i) in viewing.catalog_files"
                :key="i"
              >
                <Badge
                  variant="secondary"
                  class="font-normal"
                >
                  <button
                    v-if="isFileRef(f)"
                    type="button"
                    class="inline-flex items-center gap-1.5 hover:underline"
                    @click="download(f)"
                  >
                    <Icon
                      name="lucide:download"
                      class="size-3.5"
                    />
                    <span dir="ltr">{{ f.name }}</span>
                  </button>
                  <span
                    v-else
                    dir="ltr"
                  >{{ f }}</span>
                </Badge>
              </li>
            </ul>
          </section>
        </div>

        <DialogFooter class="border-t bg-muted/30 px-6 py-4">
          <Button
            variant="outline"
            @click="viewOpen = false"
          >
            بستن
          </Button>
          <Button
            v-if="viewing?.my_actions?.can_request_change"
            variant="outline"
            class="gap-2"
            @click="openChangeRequest(viewing)"
          >
            <Icon
              name="lucide:file-pen-line"
              class="size-4"
            /> درخواست تغییر اطلاعات
          </Button>
          <Button
            v-if="viewing?.my_actions?.can_finalize"
            variant="outline"
            class="gap-2"
            @click="finalizeRow(viewing)"
          >
            <Icon
              name="lucide:send"
              class="size-4"
            /> {{ viewing.review_status === 'NEEDS_EDIT' ? 'ثبت مجدد' : 'ثبت نهایی' }}
          </Button>
          <Button
            v-if="viewing?.my_actions?.can_edit"
            class="gap-2"
            @click="editFromView"
          >
            <Icon
              name="lucide:pencil"
              class="size-4"
            /> ویرایش
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>

    <!-- Add / edit wizard -->
    <RequestReviewDialog
      v-model:open="reviewOpen"
      :title="reviewing?.display_name ?? ''"
      :status="reviewing?.review_status ?? 'PENDING'"
      :change-request-note="reviewing?.change_request_note"
      :saving="reviewSaving"
      @submit="submitReview"
    />
    <RequestChangeRequestDialog
      v-model:open="changeOpen"
      :title="changing?.display_name ?? ''"
      :saving="changeSaving"
      @submit="submitChangeRequest"
    />

    <LazySupplierFormWizard
      v-if="wizardLoaded"
      v-model:open="formOpen"
      :supplier="editing"
      @saved="onSaved"
      @manage-categories="categoriesOpen = true"
    />

    <!-- Category management -->
    <SupplierCategoriesDialog
      v-model:open="categoriesOpen"
    />
  </ContainerWrapper>
</template>

<script setup lang="ts">
const notify = useNotify()
import { ApiError } from '~/services/backendApi'
import type { Supplier, SupplierProduct, SupplierQuality, SupplierStatus } from '~/stores/supplier'
import type { FileRef } from '~/utils/supplier-form'
import type { RequestReviewAction } from '~/utils/request-workflow'
import { PAYMENT_LABELS, isFileRef } from '~/utils/supplier-form'
import { formatJalali } from '~/utils/jalali'

definePageMeta({ title: 'تأمین‌کنندگان' })

const store = useSupplierStore()

/* ── request workflow: review (managers) · ثبت نهایی / ثبت مجدد and change request (the creator) ── */
const reviewOpen = ref(false)
const reviewing = ref<Supplier | null>(null)
const reviewSaving = ref(false)
function openReview(s: Supplier) {
  reviewing.value = s
  reviewOpen.value = true
}
async function submitReview(action: RequestReviewAction, note: string) {
  if (!reviewing.value) return
  reviewSaving.value = true
  try {
    const updated = await store.decideRequest(reviewing.value.id, action, note)
    notify.success(`«${updated.display_name}»: وضعیت درخواست به‌روزرسانی شد.`)
    reviewOpen.value = false
    if (viewing.value?.id === updated.id) viewing.value = updated
  }
  catch (e) {
    notify.error(requestErrorMessage(e, 'ثبت تصمیم انجام نشد.'))
  }
  finally {
    reviewSaving.value = false
  }
}
async function finalizeRow(s: Supplier) {
  try {
    const resubmit = s.review_status === 'NEEDS_EDIT'
    const updated = await store.finalizeSupplier(s.id)
    notify.success(resubmit ? 'درخواست دوباره برای بررسی ثبت شد.' : 'درخواست ثبت نهایی شد و در صف بررسی قرار گرفت.')
    if (viewing.value?.id === s.id) viewing.value = updated
  }
  catch (e) {
    notify.error(requestErrorMessage(e, 'ثبت نهایی انجام نشد.'))
  }
}
const changeOpen = ref(false)
const changing = ref<Supplier | null>(null)
const changeSaving = ref(false)
function openChangeRequest(s: Supplier) {
  changing.value = s
  changeOpen.value = true
}
async function submitChangeRequest(reason: string) {
  if (!changing.value) return
  changeSaving.value = true
  try {
    const updated = await store.requestChange(changing.value.id, reason)
    notify.success('درخواست تغییر برای مدیر ارسال شد.')
    changeOpen.value = false
    if (viewing.value?.id === updated.id) viewing.value = updated
  }
  catch (e) {
    notify.error(requestErrorMessage(e, 'ارسال درخواست انجام نشد.'))
  }
  finally {
    changeSaving.value = false
  }
}

/* ── live filtering ──
 * Typing in the search box filters after a short pause; the dropdowns apply
 * immediately. `appliedKey` remembers what the list already reflects so the
 * Enter key / reset button don't trigger a second identical request. */
let timer: ReturnType<typeof setTimeout> | undefined
let appliedKey = ''
const filterKey = () => JSON.stringify(store.filters)

function applyNow() {
  clearTimeout(timer)
  appliedKey = filterKey()
  store.applyFilters()
}
function resetAll() {
  clearTimeout(timer)
  store.resetFilters()
  appliedKey = filterKey()
}
watch(() => ({ ...store.filters }) as Record<string, any>, (now, old) => {
  if (JSON.stringify(now) === appliedKey) return
  clearTimeout(timer)
  const onlySearch = now.search !== old.search
    && ['category', 'subcategory', 'status', 'quality', 'supplier_type'].every(k => now[k] === old[k])
  timer = setTimeout(applyNow, onlySearch ? 350 : 0)
}, { deep: true })
onBeforeUnmount(() => clearTimeout(timer))

onMounted(async () => {
  await Promise.all([store.load(), store.loadCategories(), store.loadCategoryItems()])
  appliedKey = filterKey()
  await openFromQuery()
})

/* ── a notification points here with ?open=<id>: show that request right away ── */
const route = useRoute()
async function openFromQuery() {
  const raw = Array.isArray(route.query.open) ? route.query.open[0] : route.query.open
  const id = Number(raw)
  if (!raw || !Number.isInteger(id) || id < 1) return
  try {
    openView(store.suppliers.find(x => x.id === id) ?? await store.fetchOne(id))
  }
  catch (e) {
    notify.error(requestErrorMessage(e, 'این پرونده پیدا نشد یا اجازهٔ دیدن آن را ندارید.'))
  }
  finally {
    await navigateTo({ path: route.path, query: { ...route.query, open: undefined } }, { replace: true })
  }
}
watch(() => route.query.open, (v) => { if (v) openFromQuery() })

async function download(f: FileRef) {
  try {
    await store.downloadFile(f)
  }
  catch (e) {
    notify.error(e instanceof ApiError ? e.message : 'بارگیری فایل انجام نشد.')
  }
}


/* ── Excel / Word export of the current filters (needs the module's `export` permission) ── */
const exporting = ref<'' | 'xlsx' | 'docx'>('')
async function runExport(format: 'xlsx' | 'docx') {
  exporting.value = format
  try {
    await store.exportFile(format)
  }
  catch (e) {
    notify.error(requestErrorMessage(e, 'دریافت خروجی انجام نشد.'))
  }
  finally {
    exporting.value = ''
  }
}
const pageCount = computed(() => Math.max(1, Math.ceil(store.total / store.perPage)))

function countByStatus(status: SupplierStatus) {
  return store.suppliers.filter(s => s.status === status).length
}

const statusLabel: Record<string, string> = { ACTIVE: 'فعال', SEMI_ACTIVE: 'نیمه‌فعال', INACTIVE: 'غیرفعال' }
const qualityLabel: Record<string, string> = { EXCELLENT: 'عالی', MEDIUM: 'متوسط', WEAK: 'ضعیف' }

const categoryModel = computed({
  get: () => store.filters.category || 'all',
  set: (v: string) => {
    store.filters.category = v === 'all' ? '' : v
    store.filters.subcategory = '' // the old sub-category belonged to the previous category
  },
})
// Sub-category filter. With a main category chosen it lists that category's
// sub-categories; with none chosen it lists all of them as "main / sub", and
// picking one also sets the main category (names can repeat across parents).
// Inactive entries are included: suppliers may still use them.
const subcategoryOptions = computed(() => {
  const roots = store.categoryItems.filter(c => !c.parent_id)
  const nameOf = new Map(roots.map(r => [r.id, r.name]))
  const chosen = store.filters.category
  return store.categoryItems
    .filter(c => c.parent_id && (!chosen || nameOf.get(c.parent_id) === chosen))
    .map(c => ({ id: c.id, name: c.name, parent: nameOf.get(c.parent_id!) ?? '', label: chosen ? c.name : `${nameOf.get(c.parent_id!)} / ${c.name}` }))
})
const subcategoryModel = computed({
  get: () => {
    const sub = store.filters.subcategory
    if (!sub) return 'all'
    const hit = subcategoryOptions.value.find(o => o.name === sub && (!store.filters.category || o.parent === store.filters.category))
    return hit ? String(hit.id) : 'all'
  },
  set: (v: string) => {
    if (v === 'all') { store.filters.subcategory = ''; return }
    const hit = subcategoryOptions.value.find(o => String(o.id) === v)
    if (!hit) return
    store.filters.category = hit.parent
    store.filters.subcategory = hit.name
  },
})
const statusModel = computed({
  get: () => store.filters.status || 'all',
  set: (v: string) => { store.filters.status = v === 'all' ? '' : v as SupplierStatus },
})
const qualityModel = computed({
  get: () => store.filters.quality || 'all',
  set: (v: string) => { store.filters.quality = v === 'all' ? '' : v as SupplierQuality },
})

// Products whose name/specs contain the search text (shown under the supplier's name).
function matchedProducts(s: Supplier): SupplierProduct[] {
  const t = store.filters.search.trim().toLowerCase()
  if (!t) return []
  return (s.products ?? [])
    .filter(p => `${p.name ?? ''} ${p.specs ?? ''}`.toLowerCase().includes(t))
    .slice(0, 3)
}

async function setStatus(s: Supplier, status: SupplierStatus) {
  try {
    await store.review(s.id, { status })
    notify.success(`${s.display_name}: وضعیت به «${statusLabel[status]}» تغییر کرد.`)
  }
  catch (err) {
    notify.error(err instanceof ApiError ? err.message : 'به‌روزرسانی وضعیت انجام نشد.')
  }
}
async function setQuality(s: Supplier, quality: SupplierQuality | null) {
  try {
    await store.review(s.id, { quality })
    notify.success(`کیفیت ${s.display_name} به‌روزرسانی شد.`)
  }
  catch (err) {
    notify.error(err instanceof ApiError ? err.message : 'به‌روزرسانی کیفیت انجام نشد.')
  }
}

/* ── supplier title in the table ── */
// «نام - برند/مغازه» برای شخص حقیقی؛ شخص حقوقی فقط نام شرکت
const supplierTitle = (s: Supplier) =>
  s.supplier_type === 'INDIVIDUAL' && s.brand_name?.trim()
    ? `${s.display_name} - ${s.brand_name.trim()}`
    : s.display_name

/* ── contact persons ── */
type ContactLike = {
  first_name: string
  last_name: string
  position: string
  email?: string | null
  mobile?: string | null
  landline?: string | null
}
const contactName = (c: ContactLike) => `${c.first_name} ${c.last_name}`.trim()
const primaryNumber = (c: ContactLike) => c.mobile || c.landline || ''

/* ── view ── */
const viewOpen = ref(false)
const viewing = ref<(Supplier & Record<string, any>) | null>(null)
function openView(s: Supplier) {
  viewing.value = s
  viewOpen.value = true
}
const legalRows = computed(() => [
  { label: 'نام شرکت', value: viewing.value?.company_name },
  { label: 'شناسه ملی', value: viewing.value?.company_national_id },
  { label: 'شماره ثبت', value: viewing.value?.registration_number },
  { label: 'نوع شرکت', value: viewing.value?.company_type },
  { label: 'تاریخ تأسیس', value: formatJalali(viewing.value?.established_date) },
])
const individualRows = computed(() => [
  { label: 'نام', value: viewing.value?.first_name },
  { label: 'نام خانوادگی', value: viewing.value?.last_name },
  { label: 'کد ملی', value: viewing.value?.national_id },
  { label: 'نام برند یا مغازه', value: viewing.value?.brand_name },
])
const activityList = computed(() =>
  (viewing.value?.activity_type ?? '').split(',').map((x: string) => x.trim()).filter(Boolean),
)
function paymentText(p: { payment?: string | null, creditMonths?: number | null }) {
  const label = p.payment ? PAYMENT_LABELS[p.payment] ?? p.payment : 'روش پرداخت تعیین نشده'
  return p.creditMonths ? `${label} · ${p.creditMonths} ماه` : label
}

/* ── add / edit ── */
const formOpen = ref(false)
// the big wizard is downloaded only when it is first opened (keeps the list page fast to load)
const wizardLoaded = ref(false)
watch(formOpen, (v) => { if (v) wizardLoaded.value = true })
const editing = ref<Supplier | null>(null)
function openCreate() {
  editing.value = null
  formOpen.value = true
}
function openEdit(s: Supplier) {
  editing.value = s
  formOpen.value = true
}
function editFromView() {
  if (!viewing.value) return
  viewOpen.value = false
  openEdit(viewing.value)
}
async function onSaved() {
  await Promise.all([store.load(), store.loadCategories()])
}

/* ── categories ── */
const categoriesOpen = ref(false)

/* ── delete ── */
async function confirmDelete(s: Supplier) {
  if (!window.confirm(`تأمین‌کننده «${s.display_name}» حذف شود؟ این کار از اینجا قابل بازگشت نیست.`)) return
  try {
    await store.removeSupplier(s.id)
    notify.success(`تأمین‌کننده ${s.display_name} حذف شد.`)
  }
  catch (err) {
    notify.error(err instanceof ApiError ? err.message : 'حذف تأمین‌کننده انجام نشد.')
  }
}
</script>