<!-- /components/customer/FormWizard.vue  → <CustomerFormWizard /> -->
<template>
  <Dialog :open="open" @update:open="v => emit('update:open', v)">
    <DialogContent
      dir="rtl"
      class="flex max-h-[92vh] flex-col gap-0 overflow-hidden p-0 sm:max-w-3xl [&_input:not([dir=ltr])]:text-right [&_textarea:not([dir=ltr])]:text-right"
      @interact-outside.prevent
    >
      <!-- Header -->
      <DialogHeader class="border-b px-4 py-4 text-right sm:px-6">
        <DialogTitle class="text-lg font-semibold">
          {{ isEdit ? 'ویرایش مشتری' : 'مشتری جدید' }}
        </DialogTitle>
        <DialogDescription class="sr-only">
          فرم شش‌مرحله‌ای برای {{ isEdit ? 'ویرایش' : 'افزودن' }} مشتری.
        </DialogDescription>
      </DialogHeader>

      <!-- Step indicator (scrollable; the active step is kept in view automatically) -->
      <div class="px-4 pb-2 pt-5 sm:px-6">
        <div
          ref="scrollerEl"
          class="-mx-1 overflow-x-auto px-1 py-1 [scrollbar-width:thin]"
          @wheel="onStepsWheel"
        >
          <ol class="flex w-max min-w-full items-center gap-2" aria-label="روند ثبت اطلاعات">
            <template v-for="(s, i) in steps" :key="s.key">
              <li
                class="flex shrink-0 items-center"
                :aria-current="i === step ? 'step' : undefined"
              >
                <button
                  type="button"
                  class="flex items-center gap-2 rounded-full focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                  :disabled="i > furthest"
                  :title="s.title"
                  :aria-label="`مرحله ${i + 1}: ${s.title}`"
                  @click="goTo(i)"
                >
                  <span
                    class="grid size-8 shrink-0 place-items-center rounded-full text-sm font-semibold transition-colors sm:size-9"
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
                    v-if="i === step"
                    class="hidden whitespace-nowrap pe-1 text-sm font-medium text-primary sm:inline"
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
        </div>
        <p class="mt-2 text-sm font-medium text-primary sm:hidden">
          مرحله {{ fmtNum(step + 1) }} از {{ fmtNum(steps.length) }} · {{ steps[step].title }}
        </p>
      </div>

      <!-- Body -->
      <div
        ref="bodyEl"
        class="flex-1 space-y-6 overflow-y-auto px-4 py-6 sm:px-6"
      >
        <!-- ───────── Step 1: basic info ───────── -->
        <template v-if="step === 0">
          <div class="space-y-2">
            <Label class="text-sm font-semibold">نوع مشتری</Label>
            <div class="grid gap-3 sm:grid-cols-2">
              <button
                v-for="t in typeCards"
                :key="t.value"
                type="button"
                class="flex items-start gap-3 rounded-xl border-2 p-4 text-right transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                :class="form.customer_type === t.value ? 'border-primary bg-primary/5' : 'border-border hover:border-muted-foreground/40'"
                :aria-pressed="form.customer_type === t.value"
                @click="form.customer_type = t.value"
              >
                <span
                  class="grid size-10 shrink-0 place-items-center rounded-lg"
                  :class="form.customer_type === t.value ? 'bg-primary text-primary-foreground' : 'bg-muted text-muted-foreground'"
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

          <!-- legal -->
          <div
            v-if="form.customer_type === 'LEGAL'"
            class="grid gap-4 sm:grid-cols-2"
          >
            <div class="space-y-1.5 sm:col-span-2">
              <Label class="font-semibold">نام شرکت <span class="text-destructive">*</span></Label>
              <Input
                v-model="form.company_name"
                dir="auto"
                :aria-invalid="!!err.company_name"
              />
              <p v-if="err.company_name" class="text-xs text-destructive">{{ err.company_name }}</p>
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
              <p v-if="err.company_national_id" class="text-xs text-destructive">{{ err.company_national_id }}</p>
            </div>
            <div class="space-y-1.5">
              <Label class="font-semibold">شماره ثبت</Label>
              <Input v-model="form.registration_number" dir="ltr" inputmode="numeric" />
            </div>
            <div class="space-y-1.5">
              <Label class="font-semibold">شناسه اقتصادی</Label>
              <Input v-model="form.economic_id" dir="ltr" inputmode="numeric" />
            </div>
            <div class="space-y-1.5">
              <Label class="font-semibold">تاریخ شروع فعالیت</Label>
              <JalaliDateInput v-model="form.activity_start_date" :max="today" />
            </div>
          </div>

          <!-- individual -->
          <div
            v-else
            class="grid gap-4 sm:grid-cols-2"
          >
            <div class="space-y-1.5">
              <Label class="font-semibold">نام <span class="text-destructive">*</span></Label>
              <Input v-model="form.first_name" dir="auto" :aria-invalid="!!err.first_name" />
              <p v-if="err.first_name" class="text-xs text-destructive">{{ err.first_name }}</p>
            </div>
            <div class="space-y-1.5">
              <Label class="font-semibold">نام خانوادگی <span class="text-destructive">*</span></Label>
              <Input v-model="form.last_name" dir="auto" :aria-invalid="!!err.last_name" />
              <p v-if="err.last_name" class="text-xs text-destructive">{{ err.last_name }}</p>
            </div>
            <div class="space-y-1.5">
              <Label class="font-semibold">کد ملی (۱۰ رقم) <span class="text-destructive">*</span></Label>
              <Input
                v-model="form.national_id"
                dir="ltr"
                maxlength="10"
                inputmode="numeric"
                :aria-invalid="!!err.national_id"
              />
              <p v-if="err.national_id" class="text-xs text-destructive">{{ err.national_id }}</p>
            </div>
            <div class="space-y-1.5">
              <Label class="font-semibold">نام شرکت یا برند <span class="font-normal text-muted-foreground">(اختیاری)</span></Label>
              <Input v-model="form.brand_name" dir="auto" maxlength="255" />
            </div>
          </div>

          <!-- contact people -->
          <div class="space-y-3">
            <div class="flex items-center justify-between">
              <div>
                <Label class="font-semibold">افراد تماس <span class="text-destructive">*</span></Label>
                <p class="text-xs text-muted-foreground">
                  برای هر فرد، نام، نام خانوادگی و سمت را وارد کنید. هر فرد می‌تواند یک شماره موبایل و یک شماره ثابت داشته باشد (حداقل یکی الزامی است). تاریخ تولد هر فرد اختیاری است.
                </p>
              </div>
              <Button
                type="button"
                variant="outline"
                size="sm"
                class="gap-1.5"
                @click="form.contacts.push(blankContact())"
              >
                <Icon name="lucide:plus" class="size-4" /> افزودن فرد
              </Button>
            </div>

            <div
              v-for="(c, i) in form.contacts"
              :key="i"
              class="space-y-3 rounded-xl border p-4"
            >
              <div class="flex items-center justify-between">
                <p class="text-sm font-semibold">فرد {{ i + 1 }}</p>
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  class="size-8 text-muted-foreground hover:text-destructive"
                  aria-label="حذف فرد"
                  :disabled="form.contacts.length <= 1"
                  @click="form.contacts.splice(i, 1)"
                >
                  <Icon name="lucide:trash-2" class="size-4" />
                </Button>
              </div>
              <div class="grid gap-3 sm:grid-cols-2">
                <div class="space-y-1.5">
                  <Label class="text-xs font-semibold">نام <span class="text-destructive">*</span></Label>
                  <Input v-model="c.first_name" dir="auto" :aria-invalid="!!err[`contact.${i}.first_name`]" />
                  <p v-if="err[`contact.${i}.first_name`]" class="text-xs text-destructive">{{ err[`contact.${i}.first_name`] }}</p>
                </div>
                <div class="space-y-1.5">
                  <Label class="text-xs font-semibold">نام خانوادگی <span class="text-destructive">*</span></Label>
                  <Input v-model="c.last_name" dir="auto" :aria-invalid="!!err[`contact.${i}.last_name`]" />
                  <p v-if="err[`contact.${i}.last_name`]" class="text-xs text-destructive">{{ err[`contact.${i}.last_name`] }}</p>
                </div>
                <!-- position: fixed list + "سایر" with a free-text box -->
                <div class="space-y-1.5">
                  <Label class="text-xs font-semibold">سمت <span class="text-destructive">*</span></Label>
                  <Select
                    :model-value="c.position_choice || NONE"
                    @update:model-value="v => setPosition(c, v === NONE ? '' : String(v))"
                  >
                    <SelectTrigger class="w-full" :aria-invalid="!!err[`contact.${i}.position`]">
                      <SelectValue placeholder="انتخاب کنید" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem :value="NONE">انتخاب کنید...</SelectItem>
                      <SelectItem v-for="pos in positionChoices" :key="pos" :value="pos">{{ pos }}</SelectItem>
                      <SelectItem :value="POSITION_OTHER">سایر</SelectItem>
                    </SelectContent>
                  </Select>
                  <Input
                    v-if="c.position_choice === POSITION_OTHER"
                    v-model="c.position_other"
                    dir="auto"
                    maxlength="100"
                    placeholder="سمت را بنویسید"
                    class="mt-1.5"
                    :aria-invalid="!!err[`contact.${i}.position`]"
                  />
                  <p v-if="err[`contact.${i}.position`]" class="text-xs text-destructive">{{ err[`contact.${i}.position`] }}</p>
                </div>
                <div class="space-y-1.5">
                  <Label class="text-xs font-semibold">ایمیل</Label>
                  <Input v-model="c.email" type="email" dir="ltr" :aria-invalid="!!err[`contact.${i}.email`]" />
                  <p v-if="err[`contact.${i}.email`]" class="text-xs text-destructive">{{ err[`contact.${i}.email`] }}</p>
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
                <!-- birth date: for every contact person, whatever the customer type -->
                <div class="space-y-1.5">
                  <Label class="text-xs font-semibold">تاریخ تولد <span class="font-normal text-muted-foreground">(اختیاری)</span></Label>
                  <JalaliDateInput v-model="c.birth_date" :max="today" />
                </div>
              </div>
              <p v-if="err[`contact.${i}.numbers`]" class="text-xs text-destructive">{{ err[`contact.${i}.numbers`] }}</p>
            </div>
            <p v-if="err.contacts" class="text-xs text-destructive">{{ err.contacts }}</p>
          </div>

          <!-- addresses -->
          <div class="grid gap-4 sm:grid-cols-2">
            <div class="space-y-1.5">
              <Label class="font-semibold">آدرس دفتر مرکزی</Label>
              <Textarea v-model="form.head_office_address" dir="auto" rows="2" />
            </div>
            <div class="space-y-1.5">
              <Label class="font-semibold">آدرس محل کارخانه</Label>
              <Textarea v-model="form.factory_address" dir="auto" rows="2" />
            </div>
            <div class="space-y-1.5">
              <Label class="font-semibold">کد پستی دفتر مرکزی</Label>
              <Input
                v-model="form.head_office_postal_code"
                dir="ltr"
                maxlength="10"
                inputmode="numeric"
                placeholder="1234567890"
                :aria-invalid="!!err.head_office_postal_code"
              />
              <p v-if="err.head_office_postal_code" class="text-xs text-destructive">{{ err.head_office_postal_code }}</p>
            </div>
            <div class="space-y-1.5">
              <Label class="font-semibold">کد پستی کارخانه</Label>
              <Input
                v-model="form.factory_postal_code"
                dir="ltr"
                maxlength="10"
                inputmode="numeric"
                placeholder="1234567890"
                :aria-invalid="!!err.factory_postal_code"
              />
              <p v-if="err.factory_postal_code" class="text-xs text-destructive">{{ err.factory_postal_code }}</p>
            </div>

            <!-- acquaintance source -->
            <div class="space-y-1.5" :class="form.acquaintance_source === 'OTHER' ? '' : 'sm:col-span-2'">
              <Label class="font-semibold">منبع آشنایی با مشتری</Label>
              <Select
                :model-value="form.acquaintance_source || NONE"
                @update:model-value="v => setSource(v === NONE ? '' : v as AcquaintanceSource)"
              >
                <SelectTrigger class="w-full"><SelectValue placeholder="انتخاب کنید" /></SelectTrigger>
                <SelectContent>
                  <SelectItem :value="NONE">مشخص نشده</SelectItem>
                  <SelectItem v-for="o in sourceOptions" :key="o.value" :value="o.value">{{ o.label }}</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div v-if="form.acquaintance_source === 'OTHER'" class="space-y-1.5">
              <Label class="font-semibold">منبع آشنایی را بنویسید <span class="text-destructive">*</span></Label>
              <Input
                v-model="form.acquaintance_source_other"
                dir="auto"
                maxlength="255"
                :aria-invalid="!!err.acquaintance_source_other"
              />
              <p v-if="err.acquaintance_source_other" class="text-xs text-destructive">{{ err.acquaintance_source_other }}</p>
            </div>
          </div>
        </template>

        <!-- ───────── Step 2: activity profile ───────── -->
        <template v-else-if="step === 1">
          <!-- industries (one or more) -->
          <div class="space-y-3">
            <div class="flex items-center justify-between gap-2">
              <div>
                <Label class="font-semibold">صنعت فعالیت <span class="text-destructive">*</span></Label>
                <p class="text-xs text-muted-foreground">اگر مشتری در چند صنعت فعالیت دارد، هر صنعت را جداگانه اضافه کنید.</p>
              </div>
              <div class="flex shrink-0 items-center gap-2">
                <Button
                  v-if="store.canUpdate"
                  type="button"
                  variant="link"
                  size="sm"
                  class="h-auto gap-1 p-0"
                  @click="emit('manage-categories')"
                >
                  <Icon name="lucide:settings-2" class="size-3.5" /> مدیریت دسته‌بندی‌ها
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  class="gap-1.5"
                  @click="form.industries.push(blankIndustry())"
                >
                  <Icon name="lucide:plus" class="size-4" /> افزودن صنعت
                </Button>
              </div>
            </div>

            <div
              v-for="(row, i) in form.industries"
              :key="i"
              class="space-y-3 rounded-xl border p-4"
            >
              <div class="flex items-center justify-between">
                <p class="text-sm font-semibold">صنعت {{ i + 1 }}</p>
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  class="size-8 text-muted-foreground hover:text-destructive"
                  aria-label="حذف صنعت"
                  :disabled="form.industries.length <= 1"
                  @click="form.industries.splice(i, 1)"
                >
                  <Icon name="lucide:trash-2" class="size-4" />
                </Button>
              </div>
              <div class="grid gap-3 sm:grid-cols-2">
                <div class="space-y-1.5">
                  <Label class="text-xs font-semibold">صنعت اصلی</Label>
                  <Select
                    :model-value="row.category || NONE"
                    @update:model-value="v => setIndustryCategory(i, v === NONE ? '' : String(v))"
                  >
                    <SelectTrigger class="w-full" :aria-invalid="!!err[`industry.${i}.category`] || (!!err.industries && i === 0)">
                      <SelectValue placeholder="یک صنعت انتخاب کنید" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem :value="NONE">انتخاب کنید...</SelectItem>
                      <SelectItem v-for="c in categoryChoicesFor(row)" :key="c" :value="c">{{ c }}</SelectItem>
                    </SelectContent>
                  </Select>
                  <p v-if="err[`industry.${i}.category`]" class="text-xs text-destructive">{{ err[`industry.${i}.category`] }}</p>
                </div>
                <div v-if="subcategoryChoicesFor(row).length" class="space-y-1.5">
                  <Label class="text-xs font-semibold">صنعت فرعی</Label>
                  <Select
                    :model-value="row.subcategory || NONE"
                    @update:model-value="v => row.subcategory = v === NONE ? '' : String(v)"
                  >
                    <SelectTrigger class="w-full">
                      <SelectValue placeholder="یک مورد فرعی انتخاب کنید" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem :value="NONE">بدون صنعت فرعی</SelectItem>
                      <SelectItem v-for="c in subcategoryChoicesFor(row)" :key="c" :value="c">{{ c }}</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
            </div>
            <p v-if="err.industries" class="text-xs text-destructive">{{ err.industries }}</p>
          </div>

          <div class="space-y-2">
            <Label class="font-semibold">نوع فعالیت <span class="text-destructive">*</span></Label>
            <div class="flex flex-wrap gap-2" role="group" aria-label="نوع فعالیت">
              <button
                v-for="o in activityOptions"
                :key="o.value"
                type="button"
                class="rounded-full border px-3.5 py-1.5 text-sm transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                :class="form.activity_types.includes(o.value as ActivityType) ? 'border-primary bg-primary text-primary-foreground' : 'hover:bg-muted'"
                :aria-pressed="form.activity_types.includes(o.value as ActivityType)"
                @click="toggleActivity(o.value as ActivityType)"
              >
                {{ o.label }}
              </button>
            </div>
            <p v-if="err.activity_types" class="text-xs text-destructive">{{ err.activity_types }}</p>
          </div>

          <!-- produced products: yearly whole-number amount + unit (TON default / KG) -->
          <div class="space-y-3">
            <div class="flex items-center justify-between">
              <div>
                <Label class="font-semibold">محصولات تولیدی مشتری</Label>
                <p class="text-xs text-muted-foreground">برای هر محصول، میزان تولید سالانه را (به‌صورت عدد صحیح) وارد کنید.</p>
              </div>
              <Button
                type="button"
                variant="outline"
                size="sm"
                class="gap-1.5"
                @click="form.produced_products.push(blankProduced())"
              >
                <Icon name="lucide:plus" class="size-4" /> افزودن محصول
              </Button>
            </div>
            <p
              v-if="!form.produced_products.length"
              class="rounded-xl border border-dashed p-5 text-center text-sm text-muted-foreground"
            >
              هنوز محصول تولیدی ثبت نشده است.
            </p>
            <div
              v-for="(p, i) in form.produced_products"
              :key="i"
              class="space-y-3 rounded-xl border p-4"
            >
              <div class="flex items-center justify-between">
                <p class="text-sm font-semibold">محصول {{ i + 1 }}</p>
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  class="size-8 text-muted-foreground hover:text-destructive"
                  aria-label="حذف محصول"
                  @click="form.produced_products.splice(i, 1)"
                >
                  <Icon name="lucide:trash-2" class="size-4" />
                </Button>
              </div>
              <div class="grid gap-3 sm:grid-cols-4">
                <div class="space-y-1.5 sm:col-span-2">
                  <Label class="text-xs font-semibold">نام محصول <span class="text-destructive">*</span></Label>
                  <CustomerOptionSelect v-model="p.name" kind="PRODUCT" :invalid="!!err[`produced.${i}.name`]" />
                  <p v-if="err[`produced.${i}.name`]" class="text-xs text-destructive">{{ err[`produced.${i}.name`] }}</p>
                </div>
                <div class="space-y-1.5 sm:col-span-2">
                  <Label class="text-xs font-semibold">میزان تولید سالانه</Label>
                  <div class="flex gap-1.5">
                    <Input
                      v-model="p.amount"
                      dir="ltr"
                      inputmode="numeric"
                      class="min-w-0"
                      :aria-invalid="!!err[`produced.${i}.amount`]"
                    />
                    <Select :model-value="p.unit" @update:model-value="v => p.unit = unitOf(v)">
                      <SelectTrigger class="w-28 shrink-0"><SelectValue /></SelectTrigger>
                      <SelectContent>
                        <SelectItem v-for="o in unitChoices" :key="o.value" :value="o.value">{{ o.label }}</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <p v-if="err[`produced.${i}.amount`]" class="text-xs text-destructive">{{ err[`produced.${i}.amount`] }}</p>
                </div>
              </div>
            </div>
          </div>

          <!-- capacity = yearly sum of the produced products above (computed, read-only) -->
          <div class="space-y-1.5">
            <Label class="font-semibold">ظرفیت تولید کارخانه (سالانه)</Label>
            <Input :model-value="capacityText" dir="auto" class="text-right" disabled />
            <p class="text-xs text-muted-foreground">جمع میزان تولید سالانه‌ی محصولات بالا (به تن)؛ خودکار محاسبه می‌شود.</p>
          </div>

          <!-- تعداد خطوط تولید: typed by hand (independent of the names below) -->
          <div class="space-y-1.5">
            <Label class="font-semibold">تعداد خطوط تولید</Label>
            <Input
              v-model="form.production_lines_count"
              dir="ltr"
              inputmode="numeric"
              class="text-right"
              maxlength="6"
              placeholder="مثلاً ۳"
              :aria-invalid="!!err.production_lines_count"
            />
            <p v-if="err.production_lines_count" class="text-xs text-destructive">{{ err.production_lines_count }}</p>
          </div>

          <!-- نام خطوط تولید: add / remove by hand, any number -->
          <div class="space-y-3 rounded-xl border p-4">
            <div class="flex items-center justify-between gap-2">
              <p class="text-sm font-semibold">
                خطوط تولید
                <span v-if="form.production_line_names.length" class="font-normal text-muted-foreground">({{ fmtNum(form.production_line_names.length) }} خط)</span>
              </p>
              <Button type="button" variant="outline" size="sm" class="gap-1.5" @click="addLine">
                <Icon name="lucide:plus" class="size-3.5" /> افزودن خط تولید
              </Button>
            </div>
            <p v-if="!form.production_line_names.length" class="text-xs text-muted-foreground">
              هنوز خطی ثبت نشده است؛ با دکمه‌ی «افزودن خط تولید» هر تعداد که لازم است نام خط اضافه کنید.
            </p>
            <div class="grid gap-3 sm:grid-cols-2">
              <div v-for="(_, i) in form.production_line_names" :key="i" class="space-y-1.5">
                <Label class="text-xs font-semibold">نام خط تولید {{ fmtNum(i + 1) }}</Label>
                <div class="flex items-center gap-1.5">
                  <Input v-model="form.production_line_names[i]" dir="auto" maxlength="255" />
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    class="shrink-0 text-destructive hover:text-destructive"
                    title="حذف این خط"
                    aria-label="حذف این خط"
                    @click="form.production_line_names.splice(i, 1)"
                  >
                    <Icon name="lucide:trash-2" class="size-4" />
                  </Button>
                </div>
              </div>
            </div>
            <p v-if="err.production_line_names" class="text-xs text-destructive">{{ err.production_line_names }}</p>
          </div>

          <!-- location -->
          <div class="space-y-3 rounded-xl border bg-muted/30 p-4">
            <p class="text-sm font-semibold">شهر و موقعیت جغرافیایی کارخانه <span class="text-destructive">*</span></p>
            <div class="grid gap-4 sm:grid-cols-2">
              <div class="space-y-1.5">
                <Label class="text-xs font-semibold">استان <span class="text-destructive">*</span></Label>
                <Select
                  :model-value="form.factory_province || NONE"
                  @update:model-value="v => form.factory_province = v === NONE ? '' : String(v)"
                >
                  <SelectTrigger class="w-full bg-background" :aria-invalid="!!err.factory_province">
                    <SelectValue placeholder="انتخاب کنید" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem :value="NONE">انتخاب کنید...</SelectItem>
                    <SelectItem v-for="p in provinceChoices" :key="p" :value="p">{{ p }}</SelectItem>
                  </SelectContent>
                </Select>
                <p v-if="err.factory_province" class="text-xs text-destructive">{{ err.factory_province }}</p>
              </div>
              <div class="space-y-1.5">
                <Label class="text-xs font-semibold">شهر <span class="text-destructive">*</span></Label>
                <Input
                  v-model="form.factory_city"
                  dir="auto"
                  class="bg-background"
                  list="customer-city-list"
                  :aria-invalid="!!err.factory_city"
                />
                <datalist id="customer-city-list">
                  <option v-for="c in cityChoices" :key="c" :value="c" />
                </datalist>
                <p v-if="err.factory_city" class="text-xs text-destructive">{{ err.factory_city }}</p>
              </div>
              <div class="space-y-1.5 sm:col-span-2">
                <Label class="text-xs font-semibold">موقعیت (توضیح یا لینک نقشه)</Label>
                <Input v-model="form.factory_location" dir="auto" class="bg-background" placeholder="برای نمونه: شهرک صنعتی ... یا لینک نقشه" />
              </div>
              <div class="space-y-1.5">
                <Label class="text-xs font-semibold">عرض جغرافیایی</Label>
                <Input v-model="form.latitude" dir="ltr" inputmode="decimal" class="bg-background" placeholder="35.6892" :aria-invalid="!!err.latitude" />
                <p v-if="err.latitude" class="text-xs text-destructive">{{ err.latitude }}</p>
              </div>
              <div class="space-y-1.5">
                <Label class="text-xs font-semibold">طول جغرافیایی</Label>
                <Input v-model="form.longitude" dir="ltr" inputmode="decimal" class="bg-background" placeholder="51.3890" :aria-invalid="!!err.longitude" />
                <p v-if="err.longitude" class="text-xs text-destructive">{{ err.longitude }}</p>
              </div>
            </div>
          </div>
        </template>

        <!-- ───────── Step 3: product needs ───────── -->
        <template v-else-if="step === 2">
          <div class="space-y-3">
            <div class="flex items-center justify-between">
              <div>
                <Label class="font-semibold">محصولات مصرفی <span class="text-destructive">*</span></Label>
                <p class="text-xs text-muted-foreground">
                  برای هر محصولی که مشتری نیاز دارد، گرید یا مشخصات فنی و میزان مصرف (عدد صحیح) را وارد کنید. هر تعداد محصول می‌توانید اضافه کنید.
                </p>
              </div>
              <Button
                type="button"
                variant="outline"
                size="sm"
                class="gap-1.5"
                @click="form.consumed_products.push(blankConsumed())"
              >
                <Icon name="lucide:plus" class="size-4" /> افزودن محصول
              </Button>
            </div>
            <p v-if="err.consumed" class="text-xs text-destructive">{{ err.consumed }}</p>

            <div
              v-for="(p, i) in form.consumed_products"
              :key="i"
              class="space-y-3 rounded-xl border p-4"
            >
              <div class="flex items-center justify-between">
                <p class="text-sm font-semibold">محصول {{ i + 1 }}</p>
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  class="size-8 text-muted-foreground hover:text-destructive"
                  aria-label="حذف محصول"
                  :disabled="form.consumed_products.length <= 1"
                  @click="form.consumed_products.splice(i, 1)"
                >
                  <Icon name="lucide:trash-2" class="size-4" />
                </Button>
              </div>
              <div class="grid gap-3 sm:grid-cols-2">
                <div class="space-y-1.5">
                  <Label class="text-xs font-semibold">نام محصول <span class="text-destructive">*</span></Label>
                  <CustomerOptionSelect v-model="p.name" kind="PRODUCT" :invalid="!!err[`consumed.${i}.name`]" />
                  <p v-if="err[`consumed.${i}.name`]" class="text-xs text-destructive">{{ err[`consumed.${i}.name`] }}</p>
                </div>
                <div class="space-y-1.5">
                  <Label class="text-xs font-semibold">گرید یا مشخصات فنی مورد نیاز</Label>
                  <CustomerOptionSelect v-model="p.grade_specs" kind="GRADE" />
                </div>
                <!-- the unit is one per product: both selects below change the same value -->
                <div class="space-y-1.5">
                  <Label class="text-xs font-semibold">مصرف ماهانه <span class="text-destructive">*</span></Label>
                  <div class="flex gap-1.5">
                    <Input
                      v-model="p.monthly"
                      dir="ltr"
                      inputmode="numeric"
                      class="min-w-0"
                      :aria-invalid="!!err[`consumed.${i}.monthly`]"
                    />
                    <Select :model-value="p.unit" @update:model-value="v => p.unit = unitOf(v)">
                      <SelectTrigger class="w-28 shrink-0"><SelectValue /></SelectTrigger>
                      <SelectContent>
                        <SelectItem v-for="o in unitChoices" :key="o.value" :value="o.value">{{ o.label }}</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <p v-if="err[`consumed.${i}.monthly`]" class="text-xs text-destructive">{{ err[`consumed.${i}.monthly`] }}</p>
                </div>
                <div class="space-y-1.5">
                  <Label class="text-xs font-semibold">مصرف سالانه <span class="text-destructive">*</span></Label>
                  <div class="flex gap-1.5">
                    <Input
                      v-model="p.annual"
                      dir="ltr"
                      inputmode="numeric"
                      class="min-w-0"
                      :aria-invalid="!!err[`consumed.${i}.annual`]"
                    />
                    <Select :model-value="p.unit" @update:model-value="v => p.unit = unitOf(v)">
                      <SelectTrigger class="w-28 shrink-0"><SelectValue /></SelectTrigger>
                      <SelectContent>
                        <SelectItem v-for="o in unitChoices" :key="o.value" :value="o.value">{{ o.label }}</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <p v-if="err[`consumed.${i}.annual`]" class="text-xs text-destructive">{{ err[`consumed.${i}.annual`] }}</p>
                </div>
              </div>
            </div>
          </div>

          <!-- current suppliers + which grades come from each -->
          <div class="space-y-3">
            <div class="flex items-center justify-between">
              <div>
                <Label class="font-semibold">تأمین‌کنندگان فعلی مشتری</Label>
                <p class="text-xs text-muted-foreground">اختیاری؛ برای هر تأمین‌کننده، محصول و گریدی را که مشتری از او می‌خرد وارد کنید.</p>
              </div>
              <Button
                type="button"
                variant="outline"
                size="sm"
                class="gap-1.5"
                @click="form.current_suppliers.push(blankCurrentSupplier())"
              >
                <Icon name="lucide:plus" class="size-4" /> افزودن تأمین‌کننده
              </Button>
            </div>
            <div
              v-for="(s, i) in form.current_suppliers"
              :key="i"
              class="space-y-3 rounded-xl border p-3"
            >
              <div class="flex items-center gap-2">
                <Input
                  v-model="s.name"
                  dir="auto"
                  placeholder="نام تأمین‌کننده"
                  :disabled="!!s.supplier_id"
                />
                <Badge v-if="s.supplier_id" variant="secondary" class="shrink-0 font-normal">متصل به تأمین‌کننده ثبت‌شده</Badge>
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  class="size-8 shrink-0 text-muted-foreground hover:text-destructive"
                  aria-label="حذف تأمین‌کننده"
                  @click="form.current_suppliers.splice(i, 1)"
                >
                  <Icon name="lucide:trash-2" class="size-4" />
                </Button>
              </div>
              <div class="space-y-2">
                <div class="flex items-center justify-between gap-2">
                  <p class="text-xs font-semibold text-muted-foreground">گرید / محصولی که از این تأمین‌کننده مصرف می‌شود</p>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    class="h-7 gap-1 px-2 text-xs"
                    @click="s.grades.push(blankSupplierGrade())"
                  >
                    <Icon name="lucide:plus" class="size-3.5" /> افزودن گرید
                  </Button>
                </div>
                <div
                  v-for="(g, j) in s.grades"
                  :key="j"
                  class="space-y-1"
                >
                  <div class="flex items-start gap-2">
                    <div class="grid flex-1 gap-2 sm:grid-cols-2">
                      <CustomerOptionSelect v-model="g.product" kind="PRODUCT" placeholder="نام محصول" :invalid="!!err[`supplier.${i}.grade.${j}`]" />
                      <CustomerOptionSelect v-model="g.grade" kind="GRADE" placeholder="گرید" />
                    </div>
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      class="size-8 shrink-0 text-muted-foreground hover:text-destructive"
                      aria-label="حذف گرید"
                      @click="s.grades.splice(j, 1)"
                    >
                      <Icon name="lucide:x" class="size-4" />
                    </Button>
                  </div>
                  <p v-if="err[`supplier.${i}.grade.${j}`]" class="text-xs text-destructive">{{ err[`supplier.${i}.grade.${j}`] }}</p>
                </div>
              </div>
            </div>
          </div>
        </template>

        <!-- ───────── Step 4: status & cooperation ───────── -->
        <template v-else-if="step === 3">
          <div class="grid gap-4 rounded-xl border bg-muted/30 p-4 sm:grid-cols-2">
            <div class="space-y-1.5">
              <Label class="font-semibold">وضعیت تجاری <span class="text-destructive">*</span></Label>
              <Select v-model="form.commercial_status">
                <SelectTrigger class="w-full bg-background"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem v-for="o in commercialOptions" :key="o.value" :value="o.value">{{ o.label }}</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div class="space-y-1.5">
              <Label class="font-semibold">وضعیت عملیاتی</Label>
              <Select v-model="form.operational_status">
                <SelectTrigger class="w-full bg-background"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem v-for="o in operationalOptions" :key="o.value" :value="o.value">{{ o.label }}</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div class="space-y-1.5 sm:col-span-2">
              <Label class="font-semibold">مسئول پیگیری مشتری</Label>
              <Select
                :model-value="form.assigned_to_user_id ? String(form.assigned_to_user_id) : NONE"
                @update:model-value="v => form.assigned_to_user_id = v === NONE ? null : Number(v)"
              >
                <SelectTrigger class="w-full bg-background"><SelectValue placeholder="بدون مسئول" /></SelectTrigger>
                <SelectContent>
                  <SelectItem :value="NONE">بدون مسئول</SelectItem>
                  <SelectItem v-for="u in store.assignees" :key="u.id" :value="String(u.id)">{{ u.full_name }}</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <div
            v-if="form.commercial_status === 'INACTIVE_LOST' || form.operational_status === 'INACTIVE'"
            class="space-y-1.5"
          >
            <Label class="font-semibold">دلیل غیرفعال شدن یا از دست رفتن مشتری</Label>
            <Textarea v-model="form.inactive_reason" dir="auto" rows="2" />
          </div>

          <div class="space-y-3">
            <div class="flex items-center justify-between">
              <div>
                <Label class="font-semibold">تاریخ تماس‌ها</Label>
                <p class="text-xs text-muted-foreground">هر تماس را جداگانه ثبت کنید؛ قدیمی‌ترین تاریخ به‌عنوان «اولین تماس» نمایش داده می‌شود.</p>
              </div>
              <Button
                type="button"
                variant="outline"
                size="sm"
                class="gap-1.5"
                @click="form.contact_log.push(blankLog())"
              >
                <Icon name="lucide:plus" class="size-4" /> افزودن تماس
              </Button>
            </div>
            <div
              v-for="(l, i) in form.contact_log"
              :key="i"
              class="flex items-start gap-2 rounded-xl border p-3"
            >
              <div class="w-44 shrink-0 space-y-1">
                <JalaliDateInput v-model="l.date" :max="today" :invalid="!!err[`log.${i}.date`]" />
                <p v-if="err[`log.${i}.date`]" class="text-xs text-destructive">{{ err[`log.${i}.date`] }}</p>
              </div>
              <Input v-model="l.note" dir="auto" placeholder="یادداشت تماس (اختیاری)" />
              <Button
                type="button"
                variant="ghost"
                size="icon"
                class="size-8 shrink-0 text-muted-foreground hover:text-destructive"
                aria-label="حذف تماس"
                @click="form.contact_log.splice(i, 1)"
              >
                <Icon name="lucide:trash-2" class="size-4" />
              </Button>
            </div>
          </div>

          <div class="grid gap-4 sm:grid-cols-2">
            <div class="space-y-1.5">
              <Label class="font-semibold">تاریخ اولین خرید</Label>
              <JalaliDateInput v-model="form.first_purchase_date" :max="today" />
            </div>
            <div class="space-y-1.5">
              <Label class="font-semibold">تاریخ آخرین خرید</Label>
              <JalaliDateInput v-model="form.last_purchase_date" :max="today" :invalid="!!err.last_purchase_date" />
              <p v-if="err.last_purchase_date" class="text-xs text-destructive">{{ err.last_purchase_date }}</p>
            </div>
          </div>
        </template>

        <!-- ───────── Step 5: commercial terms ───────── -->
        <template v-else-if="step === 4">
          <p
            v-if="!termsApply"
            class="flex items-start gap-2 rounded-xl border border-dashed bg-muted/30 p-4 text-sm text-muted-foreground"
          >
            <Icon name="lucide:info" class="mt-0.5 size-4 shrink-0" />
            این مرحله برای مشتریانِ «در حال مذاکره فروش» و «جذب‌شده» کاربرد دارد. اگر هنوز اطلاعاتی ندارید، می‌توانید از آن عبور کنید.
          </p>

          <div class="grid gap-4 sm:grid-cols-2">
            <!-- payment terms -->
            <div class="space-y-1.5" :class="creditSelected ? '' : 'sm:col-span-2'">
              <Label class="font-semibold">شرایط پرداخت</Label>
              <Select
                :model-value="form.payment_type || NONE"
                @update:model-value="v => setPaymentType(v === NONE ? '' : v as PaymentType)"
              >
                <SelectTrigger class="w-full"><SelectValue placeholder="انتخاب کنید" /></SelectTrigger>
                <SelectContent>
                  <SelectItem :value="NONE">مشخص نشده</SelectItem>
                  <SelectItem v-for="o in paymentOptions" :key="o.value" :value="o.value">{{ o.label }}</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div v-if="creditSelected" class="space-y-1.5">
              <Label class="font-semibold">مدت اعتبار <span class="text-destructive">*</span></Label>
              <Select
                :model-value="form.credit_months || NONE"
                @update:model-value="v => form.credit_months = v === NONE ? '' : String(v)"
              >
                <SelectTrigger class="w-full" :aria-invalid="!!err.credit_months"><SelectValue placeholder="چند ماهه؟" /></SelectTrigger>
                <SelectContent>
                  <SelectItem :value="NONE">انتخاب کنید...</SelectItem>
                  <SelectItem v-for="m in creditMonthChoices" :key="m" :value="String(m)">{{ fmtNum(m) }} ماهه</SelectItem>
                  <SelectItem value="OTHER">سایر</SelectItem>
                </SelectContent>
              </Select>
              <p v-if="err.credit_months" class="text-xs text-destructive">{{ err.credit_months }}</p>
            </div>
            <div v-if="creditSelected && form.credit_months === 'OTHER'" class="space-y-1.5 sm:col-span-2">
              <Label class="font-semibold">مدت اعتبار را بنویسید <span class="text-destructive">*</span></Label>
              <Input
                v-model="form.credit_other"
                dir="auto"
                maxlength="100"
                placeholder="برای نمونه: ۱۸ ماهه یا ۴۵ روزه"
                :aria-invalid="!!err.credit_other"
              />
              <p v-if="err.credit_other" class="text-xs text-destructive">{{ err.credit_other }}</p>
            </div>
            <div class="space-y-1.5 sm:col-span-2">
              <Label class="font-semibold">توضیحات پرداخت <span class="font-normal text-muted-foreground">(اختیاری)</span></Label>
              <Textarea v-model="form.payment_terms" dir="auto" rows="2" placeholder="برای نمونه: ۳۰ درصد پیش‌پرداخت، مابقی چک" />
            </div>

            <div class="space-y-1.5">
              <Label class="font-semibold">نحوه خرید</Label>
              <Select
                :model-value="form.purchase_method || NONE"
                @update:model-value="v => form.purchase_method = v === NONE ? '' : v as PurchaseMethod"
              >
                <SelectTrigger class="w-full"><SelectValue placeholder="انتخاب کنید" /></SelectTrigger>
                <SelectContent>
                  <SelectItem :value="NONE">مشخص نشده</SelectItem>
                  <SelectItem v-for="o in purchaseOptions" :key="o.value" :value="o.value">{{ o.label }}</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div class="space-y-1.5" :class="form.delivery_choice === 'OTHER' ? '' : 'sm:col-span-1'">
              <Label class="font-semibold">نوع تحویل</Label>
              <Select
                :model-value="form.delivery_choice || NONE"
                @update:model-value="v => setDelivery(v === NONE ? '' : v as DeliveryChoice)"
              >
                <SelectTrigger class="w-full"><SelectValue placeholder="انتخاب کنید" /></SelectTrigger>
                <SelectContent>
                  <SelectItem :value="NONE">مشخص نشده</SelectItem>
                  <SelectItem v-for="o in deliveryOptions" :key="o.value" :value="o.value">{{ o.label }}</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div v-if="form.delivery_choice === 'OTHER'" class="space-y-1.5 sm:col-span-2">
              <Label class="font-semibold">نوع تحویل را بنویسید <span class="text-destructive">*</span></Label>
              <Input
                v-model="form.delivery_other"
                dir="auto"
                maxlength="255"
                :aria-invalid="!!err.delivery_other"
              />
              <p v-if="err.delivery_other" class="text-xs text-destructive">{{ err.delivery_other }}</p>
            </div>
            <div class="space-y-1.5 sm:col-span-2">
              <Label class="font-semibold">محل تخلیه</Label>
              <Textarea v-model="form.unloading_location" dir="auto" rows="2" />
            </div>
            <div class="space-y-1.5">
              <Label class="font-semibold">سقف اعتبار مصوب (ریال)</Label>
              <Input
                v-model="form.approved_credit_limit"
                dir="ltr"
                inputmode="numeric"
                :aria-invalid="!!err.approved_credit_limit"
              />
              <p v-if="err.approved_credit_limit" class="text-xs text-destructive">{{ err.approved_credit_limit }}</p>
            </div>
            <!-- credit rating -->
            <div class="space-y-1.5">
              <Label class="font-semibold">وضعیت اعتباری مشتری</Label>
              <Select
                :model-value="form.credit_rating || NONE"
                @update:model-value="v => form.credit_rating = v === NONE ? '' : v as CreditRating"
              >
                <SelectTrigger class="w-full"><SelectValue placeholder="انتخاب کنید" /></SelectTrigger>
                <SelectContent>
                  <SelectItem :value="NONE">مشخص نشده</SelectItem>
                  <SelectItem v-for="o in creditRatingOptions" :key="o.value" :value="o.value">{{ o.label }}</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </template>

        <!-- ───────── Step 6: follow-up & final sign-off ───────── -->
        <template v-else>
          <div class="grid gap-4 sm:grid-cols-2">
            <div class="space-y-1.5 sm:col-span-2">
              <Label class="font-semibold">یادداشت‌های داخلی</Label>
              <Textarea v-model="form.internal_notes" dir="auto" rows="3" />
            </div>
            <div class="space-y-1.5">
              <Label class="font-semibold">تاریخ آخرین مذاکره</Label>
              <JalaliDateInput v-model="form.last_negotiation_date" :max="today" />
            </div>
            <div class="space-y-1.5">
              <Label class="font-semibold">تاریخ پیگیری بعدی</Label>
              <JalaliDateInput v-model="form.next_follow_up_date" />
            </div>
            <div class="space-y-1.5 sm:col-span-2">
              <Label class="font-semibold">نتیجه آخرین مذاکره</Label>
              <Textarea v-model="form.last_negotiation_result" dir="auto" rows="2" />
            </div>
            <div class="space-y-1.5 sm:col-span-2">
              <Label class="font-semibold">اقدام بعدی</Label>
              <Textarea v-model="form.next_action" dir="auto" rows="2" />
            </div>
            <div class="space-y-1.5">
              <Label class="font-semibold">تاریخ ثبت</Label>
              <Input :model-value="registrationText" dir="ltr" class="text-right" disabled />
              <p class="text-xs text-muted-foreground">به‌صورت خودکار، روز ثبت اطلاعات.</p>
            </div>
            <div class="space-y-1.5">
              <Label class="font-semibold">تکمیل‌کننده</Label>
              <Input :model-value="completedBy" dir="auto" disabled />
            </div>
          </div>

          <!-- review -->
          <div class="space-y-3 rounded-xl border bg-muted/30 p-4">
            <p class="text-sm font-semibold">بازبینی اطلاعات</p>
            <dl class="grid gap-x-6 gap-y-2 text-sm sm:grid-cols-2">
              <div v-for="r in reviewRows" :key="r.label">
                <dt class="text-xs text-muted-foreground">{{ r.label }}</dt>
                <dd dir="auto">{{ r.value || '—' }}</dd>
              </div>
            </dl>
            <label
              v-if="!alreadyFinalized"
              class="flex cursor-pointer items-start gap-2 border-t pt-3 text-sm"
            >
              <input
                v-model="form.finalize"
                type="checkbox"
                class="mt-0.5 size-4 accent-[var(--primary,currentColor)]"
              >
              <span>
                <span class="font-medium">{{ isResubmission ? 'ثبت مجدد برای بررسی' : 'ثبت نهایی پرونده' }}</span>
                <span class="block text-xs text-muted-foreground">
                  {{ isResubmission ? 'اصلاحات انجام شد؛ پرونده دوباره برای بررسی مدیر ارسال شود.' : 'اطلاعات بازبینی شد و پرونده‌ی این مشتری نهایی شود؛ پس از آن مستقیم قابل ویرایش نیست.' }}
                </span>
              </span>
            </label>
            <p v-else class="flex items-center gap-1.5 border-t pt-3 text-sm text-muted-foreground">
              <Icon name="lucide:badge-check" class="size-4" /> این پرونده قبلاً ثبت نهایی شده است.
            </p>
          </div>
        </template>
      </div>

      <!-- Footer -->
      <DialogFooter class="flex-row items-center justify-between gap-2 border-t bg-muted/30 px-4 py-4 sm:justify-between sm:px-6">
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
          <Button
            v-else
            type="button"
            :disabled="saving"
            @click="submit"
          >
            {{ saving ? 'در حال ذخیره...' : isEdit ? 'ذخیره تغییرات' : 'افزودن مشتری' }}
          </Button>
        </div>
      </DialogFooter>
    </DialogContent>
  </Dialog>
</template>

<script setup lang="ts">
import { ApiError } from '~/services/backendApi'
import type { AcquaintanceSource, ActivityType, CreditRating, Customer, PaymentType, PurchaseMethod } from '~/stores/customer'
import { todayIso } from '~/utils/jalali'
import { formatJalali } from '~/utils/jalali'
import {
  ACTIVITY_LABELS, COMMERCIAL_STATUS_LABELS, CREDIT_MONTHS, CREDIT_RATING_LABELS, IRAN_PROVINCES, OPERATIONAL_LABELS,
  PAYMENT_LABELS, PURCHASE_LABELS, SOURCE_LABELS, UNIT_LABELS, CONTACT_POSITIONS, POSITION_OTHER, normalizeUnit,
  totalCapacityTons, MAX_PRODUCTION_LINES,
  blankConsumed, blankContact, blankCurrentSupplier, blankCustomerForm, blankIndustry, blankLog, blankProduced,
  DELIVERY_LABELS, blankSupplierGrade, customerToForm, formToPayload, isCreditPayment, validateCustomerStep,
} from '~/utils/customer-form'
import type {
  CustomerContactForm, CustomerFormState, DeliveryChoice, IndustryForm, StepErrors,
} from '~/utils/customer-form'

const props = defineProps<{ open: boolean, customer: Customer | null }>()
const emit = defineEmits<{
  'update:open': [value: boolean]
  'saved': []
  'manage-categories': []
}>()

const store = useCustomerStore()
const notify = useNotify()
const NONE = '__none__'
const today = todayIso()

const steps = [
  { key: 'basic', title: 'اطلاعات پایه' },
  { key: 'activity', title: 'نوع و مشخصات فعالیت' },
  { key: 'needs', title: 'نیاز محصولی' },
  { key: 'status', title: 'وضعیت و همکاری' },
  { key: 'terms', title: 'شرایط تجاری' },
  { key: 'followup', title: 'پیگیری و تأیید' },
]
const typeCards = [
  { value: 'LEGAL' as const, title: 'شخص حقوقی', text: 'شرکت ثبت‌شده با شناسه ملی مستقل.', icon: 'lucide:building-2' },
  { value: 'INDIVIDUAL' as const, title: 'شخص حقیقی', text: 'مشتری مستقل که با نام خود خرید می‌کند.', icon: 'lucide:user-round' },
]

const form = reactive<CustomerFormState>(blankCustomerForm())
const step = ref(0)
const furthest = ref(0)
const attempted = ref(false)
const saving = ref(false)
const bodyEl = ref<HTMLElement | null>(null)
const scrollerEl = ref<HTMLElement | null>(null)

/* ── نام خطوط تولید: لیست آزاد؛ هر تعداد خط را دستی اضافه یا حذف کنید ── */
function addLine() {
  if (form.production_line_names.length >= MAX_PRODUCTION_LINES) return
  form.production_line_names.push('')
}

const isEdit = computed(() => !!props.customer)
// a file sent back by the manager (NEEDS_EDIT) can be submitted again; otherwise "final" is final
const alreadyFinalized = computed(() => !!props.customer?.is_finalized && props.customer?.review_status !== 'NEEDS_EDIT')
const isResubmission = computed(() => props.customer?.review_status === 'NEEDS_EDIT')

watch(() => props.open, (isOpen) => {
  if (!isOpen) return
  store.loadOptionItems()
  Object.assign(form, props.customer ? customerToForm(props.customer) : blankCustomerForm())
  step.value = 0
  furthest.value = props.customer ? steps.length - 1 : 0 // editing: every step is reachable
  attempted.value = false
}, { immediate: true })

/* ── step indicator scrolling ── */
// keep the active step centred in the indicator
function scrollActiveStepIntoView() {
  const el = scrollerEl.value?.querySelector<HTMLElement>('[aria-current="step"]')
  el?.scrollIntoView({ behavior: 'smooth', inline: 'center', block: 'nearest' })
}

// mouse wheel scrolls the indicator sideways when it overflows
function onStepsWheel(e: WheelEvent) {
  const el = scrollerEl.value
  if (!el || el.scrollWidth <= el.clientWidth) return
  if (Math.abs(e.deltaY) > Math.abs(e.deltaX)) {
    el.scrollLeft += e.deltaY
    e.preventDefault()
  }
}

watch(step, () => nextTick(() => {
  bodyEl.value?.scrollTo({ top: 0 })
  scrollActiveStepIntoView()
}))

// Errors only show after the person tried to continue, and then stay live.
const err = computed<StepErrors>(() => (attempted.value ? validateCustomerStep(step.value, form) : {}))

/* ── option lists (API labels first, built-in labels as a fallback) ── */
const toOptions = (labels: Record<string, string>) => Object.entries(labels).map(([value, label]) => ({ value, label }))
const commercialOptions = computed(() => store.options?.commercial_statuses ?? toOptions(COMMERCIAL_STATUS_LABELS))
const operationalOptions = computed(() => store.options?.operational_statuses ?? toOptions(OPERATIONAL_LABELS))
const activityOptions = computed(() => store.options?.activity_types ?? toOptions(ACTIVITY_LABELS))
const purchaseOptions = computed(() => store.options?.purchase_methods ?? toOptions(PURCHASE_LABELS))
const sourceOptions = computed(() => store.options?.acquaintance_sources ?? toOptions(SOURCE_LABELS))
const paymentOptions = computed(() => store.options?.payment_types ?? toOptions(PAYMENT_LABELS))
const creditRatingOptions = computed(() => store.options?.credit_ratings ?? toOptions(CREDIT_RATING_LABELS))
const creditMonthChoices = computed(() => store.options?.credit_months ?? CREDIT_MONTHS)
const termsApply = computed(() =>
  (store.options?.commercial_terms_statuses ?? ['SALES_NEGOTIATION', 'ACQUIRED', 'REPEAT_ACTIVE']).includes(form.commercial_status),
)
const fmtNum = (n: number) => new Intl.NumberFormat('fa-IR').format(n)

/* ── contact position: fixed list + "سایر" with free text ── */
const positionChoices = computed(() => store.options?.contact_positions ?? CONTACT_POSITIONS)
function setPosition(c: CustomerContactForm, v: string) {
  c.position_choice = v
  if (v !== POSITION_OTHER) c.position_other = ''
}

/* ── amounts: whole numbers, unit TON (default) or KG ── */
const unitChoices = computed(() => store.options?.quantity_units ?? toOptions(UNIT_LABELS))
const unitOf = normalizeUnit

/* ── factory capacity: the yearly sum of the produced products, in tons ── */
const capacityText = computed(() => {
  const t = totalCapacityTons(form.produced_products)
  return t === null ? '—' : `${new Intl.NumberFormat('fa-IR', { maximumFractionDigits: 3 }).format(t)} تن در سال`
})

/* ── acquaintance source ── */
function setSource(v: AcquaintanceSource | '') {
  form.acquaintance_source = v
  if (v !== 'OTHER') form.acquaintance_source_other = ''
}

/* ── payment terms ── */
const creditSelected = computed(() => isCreditPayment(form.payment_type))
function setPaymentType(v: PaymentType | '') {
  form.payment_type = v
  if (!isCreditPayment(v)) {
    form.credit_months = ''
    form.credit_other = ''
  }
}

/* ── industries (admin-managed, 2 levels, one or more per customer). A saved value is
 *    always kept in its list so editing an old record never silently drops its industry. ── */
const baseCategories = computed(() => {
  const active = store.categoryItems.filter(c => !c.parent_id && c.is_active).map(c => c.name)
  return active.length ? active : store.categories
})
function categoryChoicesFor(row: IndustryForm) {
  return row.category && !baseCategories.value.includes(row.category) ? [row.category, ...baseCategories.value] : baseCategories.value
}
function subcategoryChoicesFor(row: IndustryForm) {
  const parent = store.categoryItems.find(c => !c.parent_id && c.name === row.category)
  const names = parent
    ? store.categoryItems.filter(c => c.parent_id === parent.id && c.is_active).map(c => c.name)
    : []
  return row.subcategory && !names.includes(row.subcategory) ? [row.subcategory, ...names] : names
}
function setIndustryCategory(i: number, v: string) {
  const row = form.industries[i]
  if (!row) return
  if (v !== row.category) row.subcategory = '' // the old sub-category belonged to another industry
  row.category = v
}

function toggleActivity(o: ActivityType) {
  const i = form.activity_types.indexOf(o)
  if (i >= 0) form.activity_types.splice(i, 1)
  else form.activity_types.push(o)
}

/* ── delivery type: two fixed choices + free text ── */
const deliveryOptions = [
  { value: 'CUSTOMER_FACTORY', label: DELIVERY_LABELS.CUSTOMER_FACTORY },
  { value: 'SELLER_FACTORY', label: DELIVERY_LABELS.SELLER_FACTORY },
  { value: 'OTHER', label: 'سایر' },
]
function setDelivery(v: DeliveryChoice) {
  form.delivery_choice = v
  if (v !== 'OTHER') form.delivery_other = ''
}

/* ── location: provinces + (suggested) cities already used by other customers ── */
const provinceChoices = computed(() =>
  form.factory_province && !IRAN_PROVINCES.includes(form.factory_province)
    ? [form.factory_province, ...IRAN_PROVINCES]
    : IRAN_PROVINCES,
)
const cityChoices = computed(() =>
  store.locations.find(l => l.province === form.factory_province)?.cities.map(c => c.city) ?? [],
)

/* ── final step ── */
const registrationText = computed(() => formatJalali(props.customer?.registration_date || today))
const completedBy = computed(() => props.customer?.created_by_name || 'کاربر فعلی (به‌صورت خودکار ثبت می‌شود)')
const reviewRows = computed(() => {
  const legal = form.customer_type === 'LEGAL'
  const statusLabel = commercialOptions.value.find(o => o.value === form.commercial_status)?.label
  const industries = form.industries
    .filter(i => i.category.trim())
    .map(i => [i.category, i.subcategory].filter(Boolean).join(' / '))
    .join('، ')
  return [
    { label: 'مشتری', value: legal ? form.company_name : `${form.first_name} ${form.last_name}`.trim() },
    { label: 'نوع', value: legal ? 'شخص حقوقی' : 'شخص حقیقی' },
    { label: 'صنعت فعالیت', value: industries },
    { label: 'موقعیت کارخانه', value: [form.factory_province, form.factory_city].filter(Boolean).join('، ') },
    { label: 'افراد تماس', value: String(form.contacts.length) },
    { label: 'محصولات مصرفی', value: String(form.consumed_products.filter(p => p.name.trim()).length) },
    { label: 'وضعیت تجاری', value: statusLabel },
    { label: 'پیگیری بعدی', value: formatJalali(form.next_follow_up_date) },
  ]
})

/* ── navigation ── */
function goTo(i: number) {
  if (i <= furthest.value && i !== step.value) {
    // going forward by clicking the indicator must pass validation too
    if (i > step.value && Object.keys(validateCustomerStep(step.value, form)).length) {
      attempted.value = true
      return
    }
    attempted.value = false
    step.value = i
  }
}
function next() {
  attempted.value = true
  if (Object.keys(validateCustomerStep(step.value, form)).length) return
  attempted.value = false
  step.value++
  furthest.value = Math.max(furthest.value, step.value)
}
function back() {
  attempted.value = false
  step.value--
}

async function submit() {
  // Re-check every step so nothing slips through via the step indicator.
  for (let i = 0; i < steps.length; i++) {
    if (Object.keys(validateCustomerStep(i, form)).length) {
      step.value = i
      attempted.value = true
      notify.error('ابتدا خطاهای مشخص‌شده را برطرف کنید.')
      return
    }
  }
  saving.value = true
  try {
    const payload = formToPayload(form)
    if (props.customer) {
      await store.updateCustomer(props.customer.id, payload)
      if (form.finalize && props.customer.my_actions?.can_finalize) await store.finalizeCustomer(props.customer.id)
    }
    else {
      await store.createCustomer({ ...payload, finalize: form.finalize })
    }
    notify.success(isEdit.value ? 'اطلاعات مشتری به‌روزرسانی شد.' : 'مشتری اضافه شد.')
    emit('saved')
    emit('update:open', false)
  }
  catch (e) {
    notify.error(e instanceof ApiError ? requestErrorMessage(e, e.message) : 'ذخیره مشتری انجام نشد.')
  }
  finally {
    saving.value = false
  }
}
</script>