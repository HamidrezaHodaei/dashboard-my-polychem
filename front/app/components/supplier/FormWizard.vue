<!-- /components/supplier/FormWizard.vue -->
<template>
  <Dialog :open="open" @update:open="v => emit('update:open', v)">
    <DialogContent
      dir="rtl"
      class="flex max-h-[92vh] flex-col gap-0 overflow-hidden p-0 sm:max-w-3xl [&_input:not([dir=ltr])]:text-right [&_textarea:not([dir=ltr])]:text-right"
      @interact-outside.prevent
    >
      <!-- Header -->
      <DialogHeader class="border-b px-6 py-4 text-right">
        <DialogTitle class="text-lg font-semibold">
          {{ isEdit ? 'ویرایش تأمین‌کننده' : 'تأمین‌کننده جدید' }}
        </DialogTitle>
        <DialogDescription class="sr-only">
          فرم چهارمرحله‌ای برای {{ isEdit ? 'ویرایش' : 'افزودن' }} تأمین‌کننده.
        </DialogDescription>
      </DialogHeader>

      <!-- Step indicator -->
      <ol class="flex items-center gap-2 px-6 pb-2 pt-5" aria-label="روند ثبت اطلاعات">
        <template v-for="(s, i) in steps" :key="s.key">
          <li
            class="flex shrink-0 items-center gap-2"
            :aria-current="i === step ? 'step' : undefined"
          >
            <button
              type="button"
              class="flex items-center gap-2 rounded-full focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
              :disabled="i > furthest"
              @click="goTo(i)"
            >
              <span
                class="grid size-9 place-items-center rounded-full text-sm font-semibold transition-colors"
                :class="i <= step ? 'bg-primary text-primary-foreground' : i <= furthest ? 'bg-primary/15 text-primary' : 'bg-muted text-muted-foreground'"
              >
                <Icon
                  v-if="i < step"
                  name="lucide:check"
                  class="size-4"
                />
                <template v-else>{{ i + 1 }}</template>
              </span>
              <span
                class="text-sm font-medium"
                :class="[i === step ? 'text-primary' : 'text-muted-foreground', i === step ? 'inline' : 'hidden md:inline']"
              >{{ s.title }}</span>
            </button>
          </li>
          <li
            v-if="i < steps.length - 1"
            class="h-0.5 min-w-4 flex-1 rounded-full transition-colors"
            :class="i < step ? 'bg-primary' : 'bg-border'"
            aria-hidden="true"
          />
        </template>
      </ol>

      <!-- Body -->
      <div
        ref="bodyEl"
        class="flex-1 space-y-6 overflow-y-auto px-6 py-6"
      >
        <!-- Step 1: identity -->
        <template v-if="step === 0">
          <div class="space-y-2">
            <Label class="text-sm font-semibold">نوع تأمین‌کننده</Label>
            <div class="grid gap-3 sm:grid-cols-2">
              <button
                v-for="t in typeCards"
                :key="t.value"
                type="button"
                class="flex items-start gap-3 rounded-xl border-2 p-4 text-right transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                :class="form.supplier_type === t.value ? 'border-primary bg-primary/5' : 'border-border hover:border-muted-foreground/40'"
                :aria-pressed="form.supplier_type === t.value"
                @click="form.supplier_type = t.value"
              >
                <span
                  class="grid size-10 shrink-0 place-items-center rounded-lg"
                  :class="form.supplier_type === t.value ? 'bg-primary text-primary-foreground' : 'bg-muted text-muted-foreground'"
                >
                  <Icon
                    :name="t.icon"
                    class="size-5"
                  />
                </span>
                <span>
                  <span class="block font-semibold">{{ t.title }}</span>
                  <span class="block text-sm text-muted-foreground">{{ t.text }}</span>
                </span>
              </button>
            </div>
          </div>

          <div
            v-if="form.supplier_type === 'LEGAL'"
            class="grid gap-4 sm:grid-cols-2"
          >
            <div class="space-y-1.5 sm:col-span-2">
              <Label class="font-semibold">نام شرکت <span class="text-destructive">*</span></Label>
              <Input
                v-model="form.company_name"
                dir="auto"
                :aria-invalid="!!err.company_name"
              />
              <p
                v-if="err.company_name"
                class="text-xs text-destructive"
              >
                {{ err.company_name }}
              </p>
            </div>
            <div class="space-y-1.5">
              <Label class="font-semibold">شناسه ملی (۱۱ رقم) <span class="text-destructive">*</span></Label>
              <Input
                v-model="form.company_national_id"
                dir="ltr"
                maxlength="11"
                inputmode="numeric"
                :aria-invalid="!!err.company_national_id"
              />
              <p
                v-if="err.company_national_id"
                class="text-xs text-destructive"
              >
                {{ err.company_national_id }}
              </p>
            </div>
            <div class="space-y-1.5">
              <Label class="font-semibold">شماره ثبت</Label>
              <Input
                v-model="form.registration_number"
                dir="ltr"
                inputmode="numeric"
              />
            </div>
            <div class="space-y-1.5">
              <Label class="font-semibold">نوع شرکت</Label>
              <Select
                :model-value="form.company_type || NONE"
                @update:model-value="v => form.company_type = v === NONE ? '' : String(v)"
              >
                <SelectTrigger class="w-full">
                  <SelectValue placeholder="نوع را انتخاب کنید" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem :value="NONE">
                    مشخص نشده
                  </SelectItem>
                  <SelectItem
                    v-for="o in COMPANY_TYPE_OPTIONS"
                    :key="o"
                    :value="o"
                  >
                    {{ o }}
                  </SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div class="space-y-1.5">
              <Label class="font-semibold">تاریخ تأسیس</Label>
              <JalaliDateInput
                v-model="form.established_date"
                :max="today"
              />
            </div>
          </div>

          <div
            v-else
            class="grid gap-4 sm:grid-cols-2"
          >
            <div class="space-y-1.5">
              <Label class="font-semibold">نام <span class="text-destructive">*</span></Label>
              <Input
                v-model="form.first_name"
                dir="auto"
                :aria-invalid="!!err.first_name"
              />
              <p
                v-if="err.first_name"
                class="text-xs text-destructive"
              >
                {{ err.first_name }}
              </p>
            </div>
            <div class="space-y-1.5">
              <Label class="font-semibold">نام خانوادگی <span class="text-destructive">*</span></Label>
              <Input
                v-model="form.last_name"
                dir="auto"
                :aria-invalid="!!err.last_name"
              />
              <p
                v-if="err.last_name"
                class="text-xs text-destructive"
              >
                {{ err.last_name }}
              </p>
            </div>
            <div class="space-y-1.5">
              <Label class="font-semibold">کد ملی (۱۰ رقم)</Label>
              <Input
                v-model="form.national_id"
                dir="ltr"
                maxlength="10"
                inputmode="numeric"
                :aria-invalid="!!err.national_id"
              />
              <p
                v-if="err.national_id"
                class="text-xs text-destructive"
              >
                {{ err.national_id }}
              </p>
            </div>
            <!-- نام برند یا مغازه: اختیاری، فقط شخص حقیقی -->
            <div class="space-y-1.5">
              <Label class="font-semibold">
                نام برند یا مغازه
                <span class="text-xs font-normal text-muted-foreground">(اختیاری)</span>
              </Label>
              <Input
                v-model="form.brand_name"
                dir="auto"
                maxlength="255"
                placeholder="برای نمونه: پلاستیک سازان"
                :aria-invalid="!!err.brand_name"
              />
              <p
                v-if="err.brand_name"
                class="text-xs text-destructive"
              >
                {{ err.brand_name }}
              </p>
            </div>
          </div>
        </template>

        <!-- Step 2: contact -->
        <template v-else-if="step === 1">
          <div class="space-y-3">
            <div class="flex items-center justify-between">
              <div>
                <Label class="font-semibold">افراد تماس <span class="text-destructive">*</span></Label>
                <p class="text-xs text-muted-foreground">
                  برای هر فرد، نام، نام خانوادگی و سمت را وارد کنید. هر فرد می‌تواند یک شماره موبایل و یک شماره ثابت داشته باشد (حداقل یکی الزامی است).
                </p>
              </div>
              <Button
                type="button"
                variant="outline"
                size="sm"
                class="gap-1.5"
                @click="form.contacts.push(blankContact())"
              >
                <Icon
                  name="lucide:plus"
                  class="size-4"
                /> افزودن فرد
              </Button>
            </div>

            <div
              v-for="(c, i) in form.contacts"
              :key="i"
              class="space-y-3 rounded-xl border p-4"
            >
              <div class="flex items-center justify-between">
                <p class="text-sm font-semibold">
                  فرد {{ i + 1 }}
                </p>
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  class="size-8 text-muted-foreground hover:text-destructive"
                  aria-label="حذف فرد"
                  :disabled="form.contacts.length <= 1"
                  @click="form.contacts.splice(i, 1)"
                >
                  <Icon
                    name="lucide:trash-2"
                    class="size-4"
                  />
                </Button>
              </div>

              <div class="grid gap-3 sm:grid-cols-2">
                <div class="space-y-1.5">
                  <Label class="text-xs font-semibold">نام <span class="text-destructive">*</span></Label>
                  <Input
                    v-model="c.first_name"
                    dir="auto"
                    :aria-invalid="!!err[`contact.${i}.first_name`]"
                  />
                  <p
                    v-if="err[`contact.${i}.first_name`]"
                    class="text-xs text-destructive"
                  >
                    {{ err[`contact.${i}.first_name`] }}
                  </p>
                </div>
                <div class="space-y-1.5">
                  <Label class="text-xs font-semibold">نام خانوادگی <span class="text-destructive">*</span></Label>
                  <Input
                    v-model="c.last_name"
                    dir="auto"
                    :aria-invalid="!!err[`contact.${i}.last_name`]"
                  />
                  <p
                    v-if="err[`contact.${i}.last_name`]"
                    class="text-xs text-destructive"
                  >
                    {{ err[`contact.${i}.last_name`] }}
                  </p>
                </div>
                <div class="space-y-1.5">
                  <Label class="text-xs font-semibold">سمت <span class="text-destructive">*</span></Label>
                  <!-- fixed list only (same as the customer bank); no free text -->
                  <Select
                    :model-value="c.position || POSITION_NONE"
                    @update:model-value="v => (c.position = v === POSITION_NONE ? '' : String(v))"
                  >
                    <SelectTrigger class="w-full" :aria-invalid="!!err[`contact.${i}.position`]">
                      <SelectValue placeholder="انتخاب کنید" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem :value="POSITION_NONE">انتخاب کنید...</SelectItem>
                      <SelectItem v-for="pos in positionChoices(c.position)" :key="pos" :value="pos">{{ pos }}</SelectItem>
                    </SelectContent>
                  </Select>
                  <p
                    v-if="err[`contact.${i}.position`]"
                    class="text-xs text-destructive"
                  >
                    {{ err[`contact.${i}.position`] }}
                  </p>
                </div>
                <div class="space-y-1.5">
                  <Label class="text-xs font-semibold">ایمیل</Label>
                  <Input
                    v-model="c.email"
                    type="email"
                    dir="ltr"
                    :aria-invalid="!!err[`contact.${i}.email`]"
                  />
                  <p
                    v-if="err[`contact.${i}.email`]"
                    class="text-xs text-destructive"
                  >
                    {{ err[`contact.${i}.email`] }}
                  </p>
                </div>
                <div class="space-y-1.5">
                  <Label class="text-xs font-semibold">شماره موبایل</Label>
                  <Input
                    v-model="c.mobile"
                    dir="ltr"
                    inputmode="tel"
                    placeholder="09121234567"
                    :aria-invalid="!!err[`contact.${i}.numbers`]"
                  />
                </div>
                <div class="space-y-1.5">
                  <Label class="text-xs font-semibold">شماره تلفن ثابت</Label>
                  <Input
                    v-model="c.landline"
                    dir="ltr"
                    inputmode="tel"
                    placeholder="02122898979"
                    :aria-invalid="!!err[`contact.${i}.numbers`]"
                  />
                </div>
              </div>
              <p
                v-if="err[`contact.${i}.numbers`]"
                class="text-xs text-destructive"
              >
                {{ err[`contact.${i}.numbers`] }}
              </p>
            </div>

            <p
              v-if="err.contacts"
              class="text-xs text-destructive"
            >
              {{ err.contacts }}
            </p>
          </div>

          <div class="grid gap-4 sm:grid-cols-2">
            <div class="space-y-1.5">
              <Label class="font-semibold">ایمیل شرکت / تأمین‌کننده</Label>
              <Input
                v-model="form.email"
                type="email"
                dir="ltr"
                :aria-invalid="!!err.email"
              />
              <p
                v-if="err.email"
                class="text-xs text-destructive"
              >
                {{ err.email }}
              </p>
            </div>
            <div class="space-y-1.5">
              <Label class="font-semibold">وب‌سایت</Label>
              <Input
                v-model="form.website"
                dir="ltr"
                placeholder="www.company.com"
                :aria-invalid="!!err.website"
              />
              <p
                v-if="err.website"
                class="text-xs text-destructive"
              >
                {{ err.website }}
              </p>
            </div>
            <div class="space-y-1.5">
              <Label class="font-semibold">کد پستی (۱۰ رقم)</Label>
              <Input
                v-model="form.postal_code"
                dir="ltr"
                maxlength="10"
                inputmode="numeric"
                placeholder="1234567890"
                :aria-invalid="!!err.postal_code"
              />
              <p
                v-if="err.postal_code"
                class="text-xs text-destructive"
              >
                {{ err.postal_code }}
              </p>
            </div>
            <div class="space-y-1.5 sm:col-span-2">
              <Label class="font-semibold">نشانی</Label>
              <Textarea
                v-model="form.address"
                dir="auto"
                rows="3"
              />
            </div>
          </div>
        </template>

        <!-- Step 3: business -->
        <template v-else-if="step === 2">
          <div class="space-y-1.5">
            <div class="flex items-center justify-between">
              <Label class="font-semibold">دسته‌بندی</Label>
              <Button
                v-if="store.canUpdate"
                type="button"
                variant="link"
                size="sm"
                class="h-auto gap-1 p-0"
                @click="emit('manage-categories')"
              >
                <Icon
                  name="lucide:settings-2"
                  class="size-3.5"
                /> مدیریت دسته‌بندی‌ها
              </Button>
            </div>
            <Select
              :model-value="form.category || NONE"
              @update:model-value="v => setCategory(v === NONE ? '' : String(v))"
            >
              <SelectTrigger class="w-full">
                <SelectValue placeholder="یک دسته‌بندی انتخاب کنید" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem :value="NONE">
                  بدون دسته‌بندی
                </SelectItem>
                <SelectItem
                  v-for="c in categoryChoices"
                  :key="c"
                  :value="c"
                >
                  {{ c }}
                </SelectItem>
              </SelectContent>
            </Select>
            <p class="text-xs text-muted-foreground">
              همین فهرست در فرم ثبت‌نام عمومی تأمین‌کنندگان نیز نمایش داده می‌شود.
            </p>
          </div>

          <div
            v-if="subcategoryChoices.length"
            class="space-y-1.5"
          >
            <Label class="font-semibold">دسته‌بندی فرعی</Label>
            <Select
              :model-value="form.subcategory || NONE"
              @update:model-value="v => form.subcategory = v === NONE ? '' : String(v)"
            >
              <SelectTrigger class="w-full">
                <SelectValue placeholder="یک دسته‌بندی فرعی انتخاب کنید" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem :value="NONE">
                  بدون دسته‌بندی فرعی
                </SelectItem>
                <SelectItem
                  v-for="c in subcategoryChoices"
                  :key="c"
                  :value="c"
                >
                  {{ c }}
                </SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div class="space-y-2">
            <Label class="font-semibold">نوع فعالیت</Label>
            <div
              class="flex flex-wrap gap-2"
              role="group"
              aria-label="نوع فعالیت"
            >
              <button
                v-for="o in ACTIVITY_TYPE_OPTIONS"
                :key="o"
                type="button"
                class="rounded-full border px-3.5 py-1.5 text-sm transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                :class="form.activity_types.includes(o) ? 'border-primary bg-primary text-primary-foreground' : 'hover:bg-muted'"
                :aria-pressed="form.activity_types.includes(o)"
                @click="toggleActivity(o)"
              >
                {{ o }}
              </button>
            </div>
          </div>

          <div class="grid gap-4 sm:grid-cols-2">
            <div class="space-y-1.5">
              <Label class="font-semibold">ظرفیت تأمین</Label>
              <Input
                v-model="form.capacity"
                dir="auto"
                placeholder="برای نمونه: ۲۰ تن در ماه"
              />
            </div>
            <div class="space-y-1.5">
              <Label class="font-semibold">سابقه فعالیت</Label>
              <Select
                :model-value="form.experience || NONE"
                @update:model-value="v => form.experience = v === NONE ? '' : String(v)"
              >
                <SelectTrigger class="w-full">
                  <SelectValue placeholder="انتخاب کنید" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem :value="NONE">
                    مشخص نشده
                  </SelectItem>
                  <SelectItem
                    v-for="o in EXPERIENCE_OPTIONS"
                    :key="o"
                    :value="o"
                  >
                    {{ o }}
                  </SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <div class="grid gap-4 rounded-xl border bg-muted/30 p-4 sm:grid-cols-2">
            <div class="space-y-1.5">
              <Label class="font-semibold">وضعیت</Label>
              <Select v-model="form.status">
                <SelectTrigger class="w-full bg-background">
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
            </div>
            <div class="space-y-1.5">
              <Label class="font-semibold">کیفیت</Label>
              <Select
                :model-value="form.quality ?? NONE"
                @update:model-value="v => form.quality = v === NONE ? null : v as SupplierFormState['quality']"
              >
                <SelectTrigger class="w-full bg-background">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem :value="NONE">
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
            </div>
          </div>
        </template>

        <!-- Step 4: products + files -->
        <template v-else-if="step === 3">
          <div class="space-y-3">
            <div class="flex items-center justify-between">
              <div>
                <Label class="font-semibold">کالاها و خدمات</Label>
                <p class="text-xs text-muted-foreground">
                  برای هر کالا یا خدمتی که تأمین‌کننده ارائه می‌کند، یک مورد اضافه کنید.
                </p>
              </div>
              <Button
                type="button"
                variant="outline"
                size="sm"
                class="gap-1.5"
                @click="form.products.push(blankProduct())"
              >
                <Icon
                  name="lucide:plus"
                  class="size-4"
                /> افزودن کالا
              </Button>
            </div>

            <p
              v-if="!form.products.length"
              class="rounded-xl border border-dashed p-6 text-center text-sm text-muted-foreground"
            >
              هنوز کالایی ثبت نشده است. با دکمه بالا اولین مورد را اضافه کنید.
            </p>

            <div
              v-for="(p, i) in form.products"
              :key="i"
              class="space-y-3 rounded-xl border p-4"
            >
              <div class="flex items-center justify-between">
                <p class="text-sm font-semibold">
                  کالا {{ i + 1 }}
                </p>
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  class="size-8 text-muted-foreground hover:text-destructive"
                  aria-label="حذف کالا"
                  @click="form.products.splice(i, 1)"
                >
                  <Icon
                    name="lucide:trash-2"
                    class="size-4"
                  />
                </Button>
              </div>
              <div class="grid gap-3 sm:grid-cols-2">
                <div class="space-y-1.5">
                  <Label class="text-xs font-semibold">نام کالا یا خدمت <span class="text-destructive">*</span></Label>
                  <Input
                    v-model="p.name"
                    dir="auto"
                    :aria-invalid="!!err[`product.${i}.name`]"
                  />
                  <p
                    v-if="err[`product.${i}.name`]"
                    class="text-xs text-destructive"
                  >
                    {{ err[`product.${i}.name`] }}
                  </p>
                </div>
                <div class="space-y-1.5">
                  <Label class="text-xs font-semibold">مشخصات</Label>
                  <Input
                    v-model="p.specs"
                    dir="auto"
                    placeholder="Density, viscosity, purity…"
                  />
                </div>
                <div class="space-y-1.5">
                  <Label class="text-xs font-semibold">روش پرداخت <span class="text-destructive">*</span></Label>
                  <Select
                    :model-value="p.payment || NONE"
                    @update:model-value="v => setPayment(p, v === NONE ? '' : v as FormPayment)"
                  >
                    <SelectTrigger
                      class="w-full"
                      :aria-invalid="!!err[`product.${i}.payment`]"
                    >
                      <SelectValue placeholder="انتخاب کنید" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem :value="NONE">
                        انتخاب کنید...
                      </SelectItem>
                      <SelectItem value="cash">
                        نقدی
                      </SelectItem>
                      <SelectItem value="credit">
                        اعتباری
                      </SelectItem>
                      <SelectItem value="both">
                        نقدی و اعتباری
                      </SelectItem>
                    </SelectContent>
                  </Select>
                  <p
                    v-if="err[`product.${i}.payment`]"
                    class="text-xs text-destructive"
                  >
                    {{ err[`product.${i}.payment`] }}
                  </p>
                </div>
                <div
                  v-if="p.payment === 'credit' || p.payment === 'both'"
                  class="space-y-1.5"
                >
                  <Label class="text-xs font-semibold">مدت اعتبار <span class="text-destructive">*</span></Label>
                  <Select
                    :model-value="p.creditMonths || NONE"
                    @update:model-value="v => p.creditMonths = v === NONE ? '' : String(v)"
                  >
                    <SelectTrigger
                      class="w-full"
                      :aria-invalid="!!err[`product.${i}.months`]"
                    >
                      <SelectValue placeholder="انتخاب کنید" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem :value="NONE">
                        انتخاب کنید...
                      </SelectItem>
                      <SelectItem
                        v-for="m in 12"
                        :key="m"
                        :value="String(m)"
                      >
                        {{ m }} ماه
                      </SelectItem>
                    </SelectContent>
                  </Select>
                  <p
                    v-if="err[`product.${i}.months`]"
                    class="text-xs text-destructive"
                  >
                    {{ err[`product.${i}.months`] }}
                  </p>
                </div>
                <div class="space-y-1.5 sm:col-span-2">
                  <Label class="text-xs font-semibold">توضیحات</Label>
                  <Textarea
                    v-model="p.description"
                    dir="auto"
                    rows="2"
                    placeholder="گرید، رنگ، بسته‌بندی، حداقل سفارش..."
                  />
                </div>
                <div class="space-y-1.5 sm:col-span-2">
                  <Label class="text-xs font-semibold">تصویر کالا <span class="text-destructive">*</span></Label>
                  <div
                    v-if="p.image"
                    class="flex items-center gap-2"
                  >
                    <Badge
                      variant="secondary"
                      class="gap-1.5 py-1 pl-2.5 pr-1.5 text-sm font-normal"
                    >
                      <Icon
                        name="lucide:image"
                        class="size-3.5"
                      />
                      <span dir="ltr">{{ p.image.name }}</span>
                      <button
                        type="button"
                        class="grid size-5 place-items-center rounded-full hover:bg-background"
                        :aria-label="`حذف ${p.image.name}`"
                        @click="p.image = null"
                      >
                        <Icon
                          name="lucide:x"
                          class="size-3"
                        />
                      </button>
                    </Badge>
                  </div>
                  <SupplierFileDropzone
                    v-else
                    label="بارگذاری تصویر کالا"
                    icon="lucide:image-plus"
                    :accept="IMAGE_ACCEPT"
                    :loading="uploading"
                    :invalid="!!err[`product.${i}.image`]"
                    @files="f => pickImage(p, f)"
                  />
                  <p
                    v-if="err[`product.${i}.image`]"
                    class="text-xs text-destructive"
                  >
                    {{ err[`product.${i}.image`] }}
                  </p>
                </div>
                <div class="space-y-1.5 sm:col-span-2">
                  <Label class="text-xs font-semibold">فایل برگه مشخصات</Label>
                  <div
                    v-if="p.datasheet"
                    class="flex items-center gap-2"
                  >
                    <Badge
                      variant="secondary"
                      class="gap-1.5 py-1 pl-2.5 pr-1.5 text-sm font-normal"
                    >
                      <Icon
                        name="lucide:file-text"
                        class="size-3.5"
                      />
                      <span dir="ltr">{{ fileLabel(p.datasheet) }}</span>
                      <button
                        type="button"
                        class="grid size-5 place-items-center rounded-full hover:bg-background"
                        :aria-label="`حذف ${fileLabel(p.datasheet)}`"
                        @click="p.datasheet = null"
                      >
                        <Icon
                          name="lucide:x"
                          class="size-3"
                        />
                      </button>
                    </Badge>
                  </div>
                  <SupplierFileDropzone
                    v-else
                    label="بارگذاری برگه مشخصات"
                    :accept="UPLOAD_ACCEPT"
                    :loading="uploading"
                    @files="f => pickDatasheet(p, f)"
                  />
                </div>
              </div>
            </div>
          </div>

          <div class="space-y-2">
            <div>
              <Label class="font-semibold">فایل‌های کاتالوگ</Label>
              <p class="text-xs text-muted-foreground">
                فایل‌های PDF، آفیس، تصویر یا ZIP تا {{ MAX_UPLOAD_MB }} مگابایت. می‌توانید چند فایل را هم‌زمان انتخاب یا رها کنید.
              </p>
            </div>
            <SupplierFileDropzone
              label="بارگذاری فایل‌های کاتالوگ"
              multiple
              :accept="UPLOAD_ACCEPT"
              :loading="uploading"
              @files="pickCatalog"
            />
            <ul
              v-if="form.catalog_files.length"
              class="flex flex-wrap gap-2"
            >
              <li
                v-for="(f, i) in form.catalog_files"
                :key="fileLabel(f) + i"
              >
                <Badge
                  variant="secondary"
                  class="gap-1.5 py-1 pl-2.5 pr-1.5 text-sm font-normal"
                >
                  <span dir="ltr">{{ fileLabel(f) }}</span>
                  <button
                    type="button"
                    class="grid size-5 place-items-center rounded-full hover:bg-background"
                    :aria-label="`حذف ${fileLabel(f)}`"
                    @click="form.catalog_files.splice(i, 1)"
                  >
                    <Icon
                      name="lucide:x"
                      class="size-3"
                    />
                  </button>
                </Badge>
              </li>
            </ul>
          </div>
        </template>

        <!-- ── Step 5: حساب‌های بانکی (optional, any number) ── -->
        <template v-else>
          <div class="flex items-start justify-between gap-3">
            <div>
              <Label class="font-semibold">حساب‌های بانکی</Label>
              <p class="text-xs text-muted-foreground">
                اختیاری است؛ هر تعداد حساب یا کارت لازم است اضافه کنید. همه‌ی فیلدها هم اختیاری‌اند.
              </p>
            </div>
            <Button
              type="button"
              variant="outline"
              size="sm"
              class="gap-1.5"
              @click="form.bank_accounts.push(blankBankAccount())"
            >
              <Icon
                name="lucide:plus"
                class="size-3.5"
              /> افزودن حساب
            </Button>
          </div>

          <p
            v-if="!form.bank_accounts.length"
            class="rounded-xl border border-dashed p-6 text-center text-sm text-muted-foreground"
          >
            هنوز حسابی ثبت نشده است. با دکمه‌ی «افزودن حساب» شماره کارت، شماره حساب یا شبا را همراه با نام صاحب آن اضافه کنید.
          </p>

          <div
            v-for="(b, i) in form.bank_accounts"
            :key="i"
            class="space-y-3 rounded-xl border p-4"
          >
            <div class="flex items-center justify-between">
              <p class="text-sm font-semibold">
                حساب {{ i + 1 }}
              </p>
              <Button
                type="button"
                variant="ghost"
                size="icon"
                class="size-8 text-destructive hover:text-destructive"
                title="حذف این حساب"
                aria-label="حذف این حساب"
                @click="form.bank_accounts.splice(i, 1)"
              >
                <Icon
                  name="lucide:trash-2"
                  class="size-4"
                />
              </Button>
            </div>
            <div class="grid gap-3 sm:grid-cols-2">
              <div class="space-y-1.5">
                <Label class="text-xs font-semibold">نام صاحب کارت / حساب (شخص یا شرکت)</Label>
                <Input
                  v-model="b.holder_name"
                  dir="auto"
                  maxlength="255"
                  :aria-invalid="!!err[`bank.${i}.holder_name`]"
                />
                <p
                  v-if="err[`bank.${i}.holder_name`]"
                  class="text-xs text-destructive"
                >
                  {{ err[`bank.${i}.holder_name`] }}
                </p>
              </div>
              <div class="space-y-1.5">
                <Label class="text-xs font-semibold">نام بانک</Label>
                <Input
                  v-model="b.bank_name"
                  dir="auto"
                  maxlength="100"
                  placeholder="برای نمونه: ملی، ملت، پاسارگاد"
                  :aria-invalid="!!err[`bank.${i}.bank_name`]"
                />
                <p
                  v-if="err[`bank.${i}.bank_name`]"
                  class="text-xs text-destructive"
                >
                  {{ err[`bank.${i}.bank_name`] }}
                </p>
              </div>
              <div class="space-y-1.5">
                <Label class="text-xs font-semibold">شماره کارت</Label>
                <Input
                  v-model="b.card_number"
                  dir="ltr"
                  inputmode="numeric"
                  maxlength="25"
                  placeholder="6037 9918 0000 0000"
                  :aria-invalid="!!err[`bank.${i}.card_number`]"
                />
                <p
                  v-if="err[`bank.${i}.card_number`]"
                  class="text-xs text-destructive"
                >
                  {{ err[`bank.${i}.card_number`] }}
                </p>
              </div>
              <div class="space-y-1.5">
                <Label class="text-xs font-semibold">شماره حساب</Label>
                <Input
                  v-model="b.account_number"
                  dir="ltr"
                  inputmode="numeric"
                  maxlength="30"
                  :aria-invalid="!!err[`bank.${i}.account_number`]"
                />
                <p
                  v-if="err[`bank.${i}.account_number`]"
                  class="text-xs text-destructive"
                >
                  {{ err[`bank.${i}.account_number`] }}
                </p>
              </div>
              <div class="space-y-1.5 sm:col-span-2">
                <Label class="text-xs font-semibold">شماره شبا</Label>
                <Input
                  v-model="b.sheba"
                  dir="ltr"
                  maxlength="34"
                  placeholder="IR000000000000000000000000"
                  :aria-invalid="!!err[`bank.${i}.sheba`]"
                />
                <p
                  v-if="err[`bank.${i}.sheba`]"
                  class="text-xs text-destructive"
                >
                  {{ err[`bank.${i}.sheba`] }}
                </p>
              </div>
            </div>
          </div>
        </template>
      </div>

      <!-- Footer -->
      <DialogFooter class="flex-row items-center justify-between gap-2 border-t bg-muted/30 px-6 py-4 sm:justify-between">
        <Button
          type="button"
          variant="ghost"
          :disabled="saving"
          @click="emit('update:open', false)"
        >
          انصراف
        </Button>
        <div class="flex gap-2">
          <Button
            v-if="step > 0"
            type="button"
            variant="outline"
            :disabled="saving"
            @click="back"
          >
            قبلی
          </Button>
          <Button
            v-if="step < steps.length - 1"
            type="button"
            @click="next"
          >
            بعدی
          </Button>
          <template v-else>
            <!-- save as a draft (still yours to edit) or submit for review ("ثبت نهایی") -->
            <Button
              type="button"
              variant="outline"
              :disabled="saving || uploading"
              @click="submit(false)"
            >
              {{ saving ? 'در حال ذخیره...' : isEdit ? 'ذخیره تغییرات' : 'ذخیره پیش‌نویس' }}
            </Button>
            <Button
              v-if="!isEdit || props.supplier?.my_actions?.can_finalize"
              type="button"
              :disabled="saving || uploading"
              @click="submit(true)"
            >
              {{ isEdit ? (props.supplier?.review_status === 'NEEDS_EDIT' ? 'ذخیره و ثبت مجدد' : 'ذخیره و ثبت نهایی') : 'ثبت نهایی' }}
            </Button>
          </template>
        </div>
      </DialogFooter>
    </DialogContent>
  </Dialog>
</template>

<script setup lang="ts">
const notify = useNotify()
import { ApiError } from '~/services/backendApi'
import { todayIso } from '~/utils/jalali'
import { CONTACT_POSITIONS } from '~/utils/customer-form'

const POSITION_NONE = '__none__'
// A supplier saved earlier with a position outside the list keeps it as an extra choice, so
// editing never silently wipes it; nothing new can be typed.
const positionChoices = (current: string) =>
  current && !CONTACT_POSITIONS.includes(current) ? [current, ...CONTACT_POSITIONS] : CONTACT_POSITIONS
import type { Supplier } from '~/stores/supplier'
import {
  ACTIVITY_TYPE_OPTIONS, COMPANY_TYPE_OPTIONS, EXPERIENCE_OPTIONS,
  IMAGE_ACCEPT, MAX_UPLOAD_MB, UPLOAD_ACCEPT, blankBankAccount, blankContact, blankProduct, blankSupplierForm, checkUploadFile, fileLabel,
  formToPayload, supplierToForm, validateSupplierStep,
} from '~/utils/supplier-form'
import type { FormPayment, ProductForm, StepErrors, SupplierFormState } from '~/utils/supplier-form'

const props = defineProps<{ open: boolean, supplier: Supplier | null }>()
const emit = defineEmits<{
  'update:open': [value: boolean]
  'saved': []
  'manage-categories': []
}>()

const store = useSupplierStore()
const NONE = '__none__'
const today = todayIso() // local date, Gregorian ISO (the calendar shows it in Jalali)

const steps = [
  { key: 'identity', title: 'اطلاعات هویتی' },
  { key: 'contact', title: 'اطلاعات تماس' },
  { key: 'business', title: 'کسب‌وکار' },
  { key: 'products', title: 'کالاها و فایل‌ها' },
  { key: 'bank', title: 'حساب‌های بانکی' },
]
const typeCards = [
  { value: 'LEGAL' as const, title: 'شخص حقوقی', text: 'شرکت ثبت‌شده با شناسه ملی مستقل.', icon: 'lucide:building-2' },
  { value: 'INDIVIDUAL' as const, title: 'شخص حقیقی', text: 'تأمین‌کننده مستقل که با نام خود فعالیت می‌کند.', icon: 'lucide:user-round' },
]

const form = reactive<SupplierFormState>(blankSupplierForm())
const step = ref(0)
const furthest = ref(0)
const attempted = ref(false)
const saving = ref(false)
const uploading = ref(false)
const bodyEl = ref<HTMLElement | null>(null)

const isEdit = computed(() => !!props.supplier)

watch(() => props.open, (isOpen) => {
  if (!isOpen) return
  Object.assign(form, props.supplier ? supplierToForm(props.supplier) : blankSupplierForm())
  step.value = 0
  furthest.value = props.supplier ? steps.length - 1 : 0 // editing: every step is reachable
  attempted.value = false
  uploading.value = false
}, { immediate: true })

watch(step, () => nextTick(() => bodyEl.value?.scrollTo({ top: 0 })))

// Errors only show after the person tried to continue, and then stay live.
const err = computed<StepErrors>(() => (attempted.value ? validateSupplierStep(step.value, form) : {}))

// Admin-managed categories. A supplier's current value is always kept in the
// list so editing an old record never silently drops its category.
const categoryChoices = computed(() => {
  const active = store.categoryItems.filter(c => !c.parent_id && c.is_active).map(c => c.name)
  const names = active.length ? active : store.categories
  return form.category && !names.includes(form.category) ? [form.category, ...names] : names
})

// Active sub-categories of the chosen main category (current value kept too).
const subcategoryChoices = computed(() => {
  const parent = store.categoryItems.find(c => !c.parent_id && c.name === form.category)
  const names = parent
    ? store.categoryItems.filter(c => c.parent_id === parent.id && c.is_active).map(c => c.name)
    : []
  return form.subcategory && !names.includes(form.subcategory) ? [form.subcategory, ...names] : names
})

function setCategory(v: string) {
  if (v !== form.category) form.subcategory = '' // the old sub-category belonged to another category
  form.category = v
}

function toggleActivity(o: string) {
  const i = form.activity_types.indexOf(o)
  if (i >= 0) form.activity_types.splice(i, 1)
  else form.activity_types.push(o)
}
function setPayment(p: ProductForm, v: FormPayment) {
  p.payment = v
  if (v === 'cash' || v === '') p.creditMonths = ''
}

// Upload each chosen file right away; the form keeps only the {id,name,size}
// reference the server returns, and saving the supplier attaches it.
async function uploadAll(files: File[], accept: string = UPLOAD_ACCEPT) {
  const done = []
  uploading.value = true
  try {
    for (const file of files) {
      const problem = checkUploadFile(file, accept)
      if (problem) {
        notify.error(problem)
        continue
      }
      try {
        done.push(await store.uploadFile(file))
      }
      catch (e) {
        notify.error(e instanceof ApiError ? e.message : `بارگذاری فایل «${file.name}» انجام نشد.`)
      }
    }
  }
  finally {
    uploading.value = false
  }
  return done
}
// The dropzone hands over File[] (picked, dropped or pasted).
async function pickCatalog(files: File[]) {
  const uploaded = await uploadAll(files)
  for (const f of uploaded) {
    if (!form.catalog_files.some(x => typeof x !== 'string' && x.id === f.id)) form.catalog_files.push(f)
  }
}
async function pickImage(p: ProductForm, files: File[]) {
  const [uploaded] = await uploadAll(files.slice(0, 1), IMAGE_ACCEPT)
  if (uploaded) p.image = uploaded
}
async function pickDatasheet(p: ProductForm, files: File[]) {
  const [uploaded] = await uploadAll(files.slice(0, 1))
  if (uploaded) p.datasheet = uploaded
}

function goTo(i: number) {
  if (i <= furthest.value && i !== step.value) {
    // going forward by clicking the indicator must pass validation too
    if (i > step.value && Object.keys(validateSupplierStep(step.value, form)).length) {
      attempted.value = true
      return
    }
    attempted.value = false
    step.value = i
  }
}
function next() {
  attempted.value = true
  if (Object.keys(validateSupplierStep(step.value, form)).length) return
  attempted.value = false
  step.value++
  furthest.value = Math.max(furthest.value, step.value)
}
function back() {
  attempted.value = false
  step.value--
}

async function submit(finalize = true) {
  // Re-check every step so nothing slips through via the step indicator.
  for (let i = 0; i < steps.length; i++) {
    if (Object.keys(validateSupplierStep(i, form)).length) {
      step.value = i
      attempted.value = true
      notify.error('ابتدا خطاهای مشخص‌شده را برطرف کنید.')
      return
    }
  }
  saving.value = true
  try {
    const payload = formToPayload(form)
    if (props.supplier) {
      await store.updateSupplier(props.supplier.id, payload)
      if (finalize) await store.finalizeSupplier(props.supplier.id) // → «در انتظار بررسی»
    }
    else {
      await store.createSupplier({ ...payload, is_finalized: finalize } as any)
    }
    notify.success(
      finalize
        ? (props.supplier?.review_status === 'NEEDS_EDIT' ? 'اطلاعات اصلاح و دوباره برای بررسی ثبت شد.' : 'درخواست ثبت نهایی شد و در صف بررسی قرار گرفت.')
        : isEdit.value ? 'تغییرات ذخیره شد.' : 'پیش‌نویس ذخیره شد؛ تا پیش از ثبت نهایی می‌توانید آن را ویرایش کنید.',
    )
    emit('saved')
    emit('update:open', false)
  }
  catch (e) {
    notify.error(e instanceof ApiError ? requestErrorMessage(e, e.message) : 'ذخیره تأمین‌کننده انجام نشد.')
  }
  finally {
    saving.value = false
  }
}
</script>