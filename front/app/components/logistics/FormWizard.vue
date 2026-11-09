<!-- /components/logistics/FormWizard.vue  → <LogisticsFormWizard /> -->
<!--
  Add / edit wizard for the logistics database (transport companies + drivers).
  Step 1 picks the applicant type; the remaining steps depend on it:
    COMPANY: اطلاعات شرکت → نماینده و تماس → محدوده فعالیت
    DRIVER : اطلاعات هویتی → اطلاعات تماس → وسیله نقلیه و بارگیر → محدوده فعالیت
  «محدوده فعالیت» is shared. The vehicle step exists ONLY on the driver path.
  Every option list comes from GET /api/logistics/public/reference.
-->
<template>
  <Dialog
    :open="open"
    @update:open="v => emit('update:open', v)"
  >
    <DialogContent
      dir="rtl"
      class="flex max-h-[92vh] flex-col gap-0 overflow-hidden p-0 sm:max-w-3xl [&_input:not([dir=ltr])]:text-right [&_textarea:not([dir=ltr])]:text-right"
      @interact-outside.prevent
    >
      <DialogHeader class="border-b px-6 py-4 text-right">
        <DialogTitle class="text-lg font-semibold">
          {{ isEdit ? 'ویرایش اطلاعات لجستیک' : 'ثبت متقاضی جدید لجستیک' }}
        </DialogTitle>
        <DialogDescription class="sr-only">
          ویزارد {{ isEdit ? 'ویرایش' : 'ثبت' }} شرکت حمل‌ونقل یا راننده.
        </DialogDescription>
      </DialogHeader>

      <!-- Step indicator -->
      <ol
        v-if="steps.length > 1"
        class="flex items-center gap-2 px-6 pb-2 pt-5"
        aria-label="روند ثبت اطلاعات"
      >
        <template
          v-for="(s, i) in steps"
          :key="s.key"
        >
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
        <div
          v-if="!catalog"
          class="flex items-center justify-center gap-2 p-10 text-sm text-muted-foreground"
        >
          <Icon
            name="lucide:loader-circle"
            class="size-4 animate-spin"
          />
          در حال بارگذاری فهرست‌ها...
        </div>

        <template v-else>
          <!-- ── Step 1: applicant type ── -->
          <template v-if="currentKey === 'type'">
            <div class="space-y-2">
              <Label class="text-sm font-semibold">نوع متقاضی</Label>
              <div class="grid gap-3 sm:grid-cols-2">
                <button
                  v-for="t in typeCards"
                  :key="t.value"
                  type="button"
                  class="flex items-start gap-3 rounded-xl border-2 p-4 text-right transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  :class="form.applicant_type === t.value ? 'border-primary bg-primary/5' : 'border-border hover:border-muted-foreground/40'"
                  :aria-pressed="form.applicant_type === t.value"
                  @click="chooseType(t.value)"
                >
                  <span
                    class="grid size-10 shrink-0 place-items-center rounded-lg"
                    :class="form.applicant_type === t.value ? 'bg-primary text-primary-foreground' : 'bg-muted text-muted-foreground'"
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
              <p
                v-if="err.applicant_type"
                class="text-xs text-destructive"
              >
                {{ err.applicant_type }}
              </p>
            </div>
          </template>

          <!-- ── COMPANY · اطلاعات شرکت ── -->
          <template v-else-if="currentKey === 'company_info'">
            <div class="space-y-2">
              <Label class="text-sm font-semibold">نوع شخصیت</Label>
              <div class="grid gap-3 sm:grid-cols-2">
                <button
                  v-for="o in catalog.legal_types"
                  :key="o.code"
                  type="button"
                  class="rounded-xl border-2 p-3 text-right font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  :class="form.company.entity_type === o.code ? 'border-primary bg-primary/5 text-primary' : 'border-border hover:border-muted-foreground/40'"
                  :aria-pressed="form.company.entity_type === o.code"
                  @click="form.company.entity_type = o.code as 'LEGAL' | 'INDIVIDUAL'"
                >
                  شخص {{ o.label }}
                </button>
              </div>
            </div>

            <div class="grid gap-4 sm:grid-cols-2">
              <template v-if="form.company.entity_type === 'LEGAL'">
                <LogisticsField
                  class="sm:col-span-2"
                  label="نام شرکت"
                  required
                  :error="err['company.company_name']"
                >
                  <Input
                    v-model="form.company.company_name"
                    dir="auto"
                    :aria-invalid="!!err['company.company_name']"
                  />
                </LogisticsField>
                <LogisticsField
                  label="شناسه ملی (۱۱ رقم)"
                  hint="اختیاری"
                  :error="err['company.national_id']"
                >
                  <Input
                    v-model="form.company.national_id"
                    dir="ltr"
                    maxlength="11"
                    inputmode="numeric"
                    :aria-invalid="!!err['company.national_id']"
                  />
                </LogisticsField>
                <div class="hidden sm:block" />
              </template>
              <template v-else>
                <LogisticsField
                  label="نام"
                  required
                  :error="err['company.first_name']"
                >
                  <Input
                    v-model="form.company.first_name"
                    dir="auto"
                    :aria-invalid="!!err['company.first_name']"
                  />
                </LogisticsField>
                <LogisticsField
                  label="نام خانوادگی"
                  required
                  :error="err['company.last_name']"
                >
                  <Input
                    v-model="form.company.last_name"
                    dir="auto"
                    :aria-invalid="!!err['company.last_name']"
                  />
                </LogisticsField>
              </template>

              <LogisticsField
                label="استان محل فعالیت"
                required
                :error="err['company.province']"
              >
                <Select
                  :model-value="form.company.province || undefined"
                  @update:model-value="v => { form.company.province = String(v); form.company.city = '' }"
                >
                  <SelectTrigger class="w-full">
                    <SelectValue placeholder="استان را انتخاب کنید" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem
                      v-for="p in catalog.provinces"
                      :key="p.name"
                      :value="p.name"
                    >
                      {{ p.name }}
                    </SelectItem>
                  </SelectContent>
                </Select>
              </LogisticsField>
              <LogisticsField
                label="شهر محل فعالیت"
                required
                :error="err['company.city']"
              >
                <Select
                  :model-value="form.company.city || undefined"
                  :disabled="!form.company.province"
                  @update:model-value="v => form.company.city = String(v)"
                >
                  <SelectTrigger class="w-full">
                    <SelectValue :placeholder="form.company.province ? 'شهر را انتخاب کنید' : 'ابتدا استان را انتخاب کنید'" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem
                      v-for="c in citiesOf(form.company.province)"
                      :key="c"
                      :value="c"
                    >
                      {{ c }}
                    </SelectItem>
                  </SelectContent>
                </Select>
              </LogisticsField>
              <LogisticsField
                class="sm:col-span-2"
                label="نشانی دفتر"
                required
                :error="err['company.office_address']"
              >
                <Textarea
                  v-model="form.company.office_address"
                  dir="auto"
                  rows="3"
                  :aria-invalid="!!err['company.office_address']"
                />
              </LogisticsField>
            </div>
          </template>

          <!-- ── COMPANY · نماینده و اطلاعات تماس ── -->
          <template v-else-if="currentKey === 'representative'">
            <div class="grid gap-4 sm:grid-cols-2">
              <LogisticsField
                label="نام نماینده"
                required
                :error="err['rep.first_name']"
              >
                <Input
                  v-model="form.rep.first_name"
                  dir="auto"
                  :aria-invalid="!!err['rep.first_name']"
                />
              </LogisticsField>
              <LogisticsField
                label="نام خانوادگی نماینده"
                required
                :error="err['rep.last_name']"
              >
                <Input
                  v-model="form.rep.last_name"
                  dir="auto"
                  :aria-invalid="!!err['rep.last_name']"
                />
              </LogisticsField>
              <LogisticsField
                label="سمت نماینده"
                required
                :error="err['rep.position']"
              >
                <Select
                  :model-value="form.rep.position || undefined"
                  @update:model-value="v => { form.rep.position = String(v); if (v !== 'OTHER') form.rep.position_other = '' }"
                >
                  <SelectTrigger class="w-full">
                    <SelectValue placeholder="سمت را انتخاب کنید" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem
                      v-for="o in catalog.representative_positions"
                      :key="o.code"
                      :value="o.code"
                    >
                      {{ o.label }}
                    </SelectItem>
                  </SelectContent>
                </Select>
              </LogisticsField>
              <LogisticsField
                v-if="form.rep.position === 'OTHER'"
                label="عنوان سمت"
                required
                :error="err['rep.position_other']"
              >
                <Input
                  v-model="form.rep.position_other"
                  dir="auto"
                  :aria-invalid="!!err['rep.position_other']"
                />
              </LogisticsField>
              <div
                v-else
                class="hidden sm:block"
              />
              <LogisticsField
                label="شماره موبایل"
                required
                :error="err['rep.mobile']"
              >
                <Input
                  v-model="form.rep.mobile"
                  dir="ltr"
                  inputmode="tel"
                  placeholder="09121234567"
                  :aria-invalid="!!err['rep.mobile']"
                />
              </LogisticsField>
              <LogisticsField
                label="تلفن ثابت"
                hint="اختیاری · همراه با کد شهر"
                :error="err['rep.landline']"
              >
                <Input
                  v-model="form.rep.landline"
                  dir="ltr"
                  inputmode="tel"
                  placeholder="02122334455"
                  :aria-invalid="!!err['rep.landline']"
                />
              </LogisticsField>
            </div>
          </template>

          <!-- ── DRIVER · اطلاعات هویتی ── -->
          <template v-else-if="currentKey === 'identity'">
            <div class="grid gap-4 sm:grid-cols-2">
              <LogisticsField
                label="نام"
                required
                :error="err['identity.first_name']"
              >
                <Input
                  v-model="form.identity.first_name"
                  dir="auto"
                  :aria-invalid="!!err['identity.first_name']"
                />
              </LogisticsField>
              <LogisticsField
                label="نام خانوادگی"
                required
                :error="err['identity.last_name']"
              >
                <Input
                  v-model="form.identity.last_name"
                  dir="auto"
                  :aria-invalid="!!err['identity.last_name']"
                />
              </LogisticsField>
              <LogisticsField
                label="کد ملی"
                required
                :error="err['identity.national_code']"
              >
                <Input
                  v-model="form.identity.national_code"
                  dir="ltr"
                  maxlength="10"
                  inputmode="numeric"
                  :aria-invalid="!!err['identity.national_code']"
                />
              </LogisticsField>
            </div>
          </template>

          <!-- ── DRIVER · اطلاعات تماس ── -->
          <template v-else-if="currentKey === 'contact'">
            <div class="grid gap-4 sm:grid-cols-2">
              <LogisticsField
                label="شماره موبایل"
                required
                :error="err['contact.mobile']"
              >
                <Input
                  v-model="form.contact.mobile"
                  dir="ltr"
                  inputmode="tel"
                  placeholder="09121234567"
                  :aria-invalid="!!err['contact.mobile']"
                />
              </LogisticsField>
              <LogisticsField
                label="تلفن جایگزین"
                hint="اختیاری · موبایل یا تلفن ثابت"
                :error="err['contact.alt_phone']"
              >
                <Input
                  v-model="form.contact.alt_phone"
                  dir="ltr"
                  inputmode="tel"
                  :aria-invalid="!!err['contact.alt_phone']"
                />
              </LogisticsField>
            </div>
          </template>

          <!-- ── DRIVER · وسیله نقلیه و بارگیر (driver path only) ── -->
          <template v-else-if="currentKey === 'vehicle'">
            <div class="grid gap-4 sm:grid-cols-2">
              <LogisticsField
                label="نوع خودرو"
                required
                :error="err['vehicle.vehicle_type']"
              >
                <Select
                  :model-value="form.vehicle.vehicle_type || undefined"
                  @update:model-value="v => { form.vehicle.vehicle_type = String(v); if (v !== 'OTHER') form.vehicle.vehicle_type_other = '' }"
                >
                  <SelectTrigger class="w-full">
                    <SelectValue placeholder="نوع خودرو را انتخاب کنید" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem
                      v-for="o in catalog.vehicle_types"
                      :key="o.code"
                      :value="o.code"
                    >
                      {{ o.label }}
                    </SelectItem>
                  </SelectContent>
                </Select>
              </LogisticsField>
              <LogisticsField
                v-if="form.vehicle.vehicle_type === 'OTHER'"
                label="نوع خودرو (توضیح)"
                required
                :error="err['vehicle.vehicle_type_other']"
              >
                <Input
                  v-model="form.vehicle.vehicle_type_other"
                  dir="auto"
                  :aria-invalid="!!err['vehicle.vehicle_type_other']"
                />
              </LogisticsField>
              <div
                v-else
                class="hidden sm:block"
              />

              <LogisticsField
                label="نوع بارگیر یا اتاق"
                required
                :error="err['vehicle.body_type']"
              >
                <Select
                  :model-value="form.vehicle.body_type || undefined"
                  @update:model-value="v => { form.vehicle.body_type = String(v); if (v !== 'OTHER') form.vehicle.body_type_other = '' }"
                >
                  <SelectTrigger class="w-full">
                    <SelectValue placeholder="نوع بارگیر را انتخاب کنید" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem
                      v-for="o in catalog.body_types"
                      :key="o.code"
                      :value="o.code"
                    >
                      {{ o.label }}
                    </SelectItem>
                  </SelectContent>
                </Select>
              </LogisticsField>
              <LogisticsField
                v-if="form.vehicle.body_type === 'OTHER'"
                label="نوع بارگیر (توضیح)"
                required
                :error="err['vehicle.body_type_other']"
              >
                <Input
                  v-model="form.vehicle.body_type_other"
                  dir="auto"
                  :aria-invalid="!!err['vehicle.body_type_other']"
                />
              </LogisticsField>
              <div
                v-else
                class="hidden sm:block"
              />

              <LogisticsField
                label="ظرفیت حمل (تن)"
                required
                :error="err['vehicle.capacity_tons']"
              >
                <Input
                  v-model="form.vehicle.capacity_tons"
                  dir="ltr"
                  inputmode="decimal"
                  placeholder="12.5"
                  :aria-invalid="!!err['vehicle.capacity_tons']"
                />
              </LogisticsField>
            </div>

            <LogisticsField
              label="نوع کالاهای قابل حمل"
              required
              :error="err['vehicle.cargo_types']"
              hint="می‌توانید چند مورد را انتخاب کنید."
            >
              <LogisticsChecklist
                v-model="form.vehicle.cargo_types"
                :options="catalog.cargo_types"
                :invalid="!!err['vehicle.cargo_types']"
              />
            </LogisticsField>
            <LogisticsField
              v-if="form.vehicle.cargo_types.includes('OTHER')"
              label="نوع کالا (توضیح)"
              required
              :error="err['vehicle.cargo_type_other']"
            >
              <Input
                v-model="form.vehicle.cargo_type_other"
                dir="auto"
                :aria-invalid="!!err['vehicle.cargo_type_other']"
              />
            </LogisticsField>
          </template>

          <!-- ── shared · محدوده فعالیت ── -->
          <template v-else-if="currentKey === 'service_area'">
            <div class="space-y-2">
              <Label class="text-sm font-semibold">نوع محدوده فعالیت <span class="text-destructive">*</span></Label>
              <div class="grid gap-3 sm:grid-cols-4">
                <button
                  v-for="o in catalog.area_types"
                  :key="o.code"
                  type="button"
                  class="rounded-xl border-2 p-3 text-center font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  :class="form.area.area_type === o.code ? 'border-primary bg-primary/5 text-primary' : 'border-border hover:border-muted-foreground/40'"
                  :aria-pressed="form.area.area_type === o.code"
                  @click="setAreaType(form, o.code as AreaType, catalog)"
                >
                  {{ o.label }}
                </button>
              </div>
              <p
                v-if="err['area.area_type']"
                class="text-xs text-destructive"
              >
                {{ err['area.area_type'] }}
              </p>
            </div>

            <!-- coverage: city / province / provinces -->
            <div
              v-if="form.area.area_type"
              class="space-y-3"
            >
              <div class="flex items-center justify-between">
                <Label class="text-sm font-semibold">
                  {{ coverageTitle }}
                  <span
                    v-if="form.area.area_type !== 'INTERNATIONAL'"
                    class="text-destructive"
                  >*</span>
                </Label>
                <Button
                  v-if="canAddProvince"
                  type="button"
                  variant="outline"
                  size="sm"
                  class="gap-1.5"
                  @click="form.area.coverage.push(blankCoverage())"
                >
                  <Icon
                    name="lucide:plus"
                    class="size-3.5"
                  /> افزودن استان
                </Button>
              </div>

              <div
                v-for="(row, i) in form.area.coverage"
                :key="i"
                class="space-y-3 rounded-xl border p-4"
              >
                <div class="flex items-end gap-2">
                  <LogisticsField
                    class="flex-1"
                    label="استان"
                  >
                    <Select
                      :model-value="row.province || undefined"
                      @update:model-value="v => changeRowProvince(row, String(v))"
                    >
                      <SelectTrigger class="w-full">
                        <SelectValue placeholder="استان را انتخاب کنید" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem
                          v-for="p in catalog.provinces"
                          :key="p.name"
                          :value="p.name"
                          :disabled="usedElsewhere(i, p.name)"
                        >
                          {{ p.name }}
                        </SelectItem>
                      </SelectContent>
                    </Select>
                  </LogisticsField>
                  <Button
                    v-if="canRemoveProvince"
                    type="button"
                    variant="ghost"
                    size="icon"
                    class="text-destructive"
                    aria-label="حذف استان"
                    @click="form.area.coverage.splice(i, 1)"
                  >
                    <Icon
                      name="lucide:trash-2"
                      class="size-4"
                    />
                  </Button>
                </div>

                <template v-if="row.province">
                  <!-- شهری: exactly one city -->
                  <LogisticsField
                    v-if="form.area.area_type === 'CITY'"
                    label="شهر محل فعالیت"
                  >
                    <Select
                      :model-value="row.cities[0] || undefined"
                      @update:model-value="v => row.cities = [String(v)]"
                    >
                      <SelectTrigger class="w-full">
                        <SelectValue placeholder="شهر را انتخاب کنید" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem
                          v-for="c in citiesOf(row.province)"
                          :key="c"
                          :value="c"
                        >
                          {{ c }}
                        </SelectItem>
                      </SelectContent>
                    </Select>
                  </LogisticsField>

                  <!-- other types: whole province or chosen cities -->
                  <template v-else>
                    <label class="flex cursor-pointer items-center gap-2 text-sm font-medium">
                      <Checkbox
                        :model-value="row.all_cities"
                        @update:model-value="v => { row.all_cities = !!v; if (v) row.cities = [] }"
                      />
                      کل استان
                    </label>
                    <LogisticsChecklist
                      v-if="!row.all_cities"
                      v-model="row.cities"
                      :options="cityOptions(row.province)"
                    />
                  </template>
                </template>
              </div>
              <p
                v-if="err['area.coverage']"
                class="text-xs text-destructive"
              >
                {{ err['area.coverage'] }}
              </p>
            </div>

            <!-- بین‌المللی: countries + permits -->
            <template v-if="form.area.area_type === 'INTERNATIONAL'">
              <div class="grid gap-4 sm:grid-cols-2">
                <LogisticsField
                  label="کشورهای مبدأ"
                  required
                  :error="err['area.origin_countries']"
                >
                  <LogisticsChecklist
                    v-model="form.area.origin_countries"
                    :options="catalog.countries"
                    :invalid="!!err['area.origin_countries']"
                  />
                </LogisticsField>
                <LogisticsField
                  label="کشورهای مقصد"
                  required
                  :error="err['area.destination_countries']"
                  hint="حداقل یک کشور غیر از ایران لازم است."
                >
                  <LogisticsChecklist
                    v-model="form.area.destination_countries"
                    :options="catalog.countries"
                    :invalid="!!err['area.destination_countries']"
                  />
                </LogisticsField>
              </div>

              <div class="space-y-3">
                <div>
                  <Label class="text-sm font-semibold">مجوزهای بین‌المللی</Label>
                  <p class="text-xs text-muted-foreground">
                    فایل PDF یا تصویر تا {{ MAX_UPLOAD_MB }} مگابایت. موارد ستاره‌دار الزامی‌اند.
                  </p>
                </div>
                <div
                  v-for="def in permitDefs"
                  :key="def.code"
                  class="space-y-3 rounded-xl border p-4"
                  :class="err[`area.permit.${def.code}`] ? 'border-destructive' : ''"
                >
                  <div class="flex items-center justify-between gap-2">
                    <span class="font-medium">
                      {{ def.label }}
                      <span
                        v-if="def.required"
                        class="text-destructive"
                      >*</span>
                    </span>
                    <label
                      v-if="!def.required"
                      class="flex cursor-pointer items-center gap-2 text-sm"
                    >
                      <Checkbox
                        :model-value="!!permitRow(def.code)"
                        @update:model-value="v => togglePermit(def.code, !!v)"
                      />
                      دارم
                    </label>
                  </div>
                  <template v-if="permitRow(def.code)">
                    <div class="grid gap-3 sm:grid-cols-2">
                      <LogisticsField label="شماره مجوز">
                        <Input
                          :model-value="permitRow(def.code)?.number ?? ''"
                          dir="ltr"
                          @update:model-value="v => setPermitField(def.code, 'number', String(v ?? ''))"
                        />
                      </LogisticsField>
                      <LogisticsField label="تاریخ انقضا">
                        <JalaliDateInput
                          :model-value="permitRow(def.code)?.expires_at ?? ''"
                          @update:model-value="v => setPermitField(def.code, 'expires_at', String(v ?? ''))"
                        />
                      </LogisticsField>
                    </div>
                    <div
                      v-if="permitRow(def.code)?.file"
                      class="flex items-center gap-2"
                    >
                      <Badge
                        variant="secondary"
                        class="gap-1.5 py-1 pl-2.5 pr-1.5 text-sm font-normal"
                      >
                        <span dir="ltr">{{ permitRow(def.code)?.file?.name }}</span>
                        <button
                          type="button"
                          class="grid size-5 place-items-center rounded-full hover:bg-background"
                          aria-label="حذف فایل"
                          @click="setPermitField(def.code, 'file', null)"
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
                      :label="`بارگذاری ${def.label}`"
                      :accept="PERMIT_ACCEPT"
                      :loading="uploading"
                      :invalid="!!err[`area.permit.${def.code}`]"
                      @files="f => pickPermit(def.code, f)"
                    />
                  </template>
                  <p
                    v-if="err[`area.permit.${def.code}`]"
                    class="text-xs text-destructive"
                  >
                    {{ err[`area.permit.${def.code}`] }}
                  </p>
                </div>
                <p
                  v-if="err['area.permits']"
                  class="text-xs text-destructive"
                >
                  {{ err['area.permits'] }}
                </p>
              </div>
            </template>

            <!-- initial status (create only; deciding it needs the `review` permission) -->
            <LogisticsField
              v-if="!isEdit && canChooseStatus"
              label="وضعیت ثبت"
              hint="متقاضیانی که کارمند اضافه می‌کند می‌توانند مستقیم تأیید شوند."
            >
              <Select
                :model-value="form.status"
                @update:model-value="v => form.status = v as ApplicantStatus"
              >
                <SelectTrigger class="w-full sm:w-64">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem
                    v-for="code in (['PENDING', 'APPROVED', 'REJECTED'] as const)"
                    :key="code"
                    :value="code"
                  >
                    {{ STATUS_LABELS[code] }}
                  </SelectItem>
                </SelectContent>
              </Select>
            </LogisticsField>
          </template>
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
            :disabled="saving || checking"
            @click="back"
          >
            قبلی
          </Button>
          <Button
            v-if="step < steps.length - 1"
            type="button"
            :disabled="!catalog || checking"
            @click="next"
          >
            {{ checking ? 'در حال بررسی...' : 'بعدی' }}
          </Button>
          <template v-else>
            <!-- create: save as a draft (still yours to edit) or submit for review ("ثبت نهایی") -->
            <Button
              type="button"
              variant="outline"
              :disabled="!catalog || saving || uploading || !form.applicant_type"
              @click="submit(false)"
            >
              {{ saving ? 'در حال ذخیره...' : isEdit ? 'ذخیره تغییرات' : 'ذخیره پیش‌نویس' }}
            </Button>
            <Button
              v-if="!isEdit || props.applicant?.my_actions?.can_finalize"
              type="button"
              :disabled="!catalog || saving || uploading || !form.applicant_type"
              @click="submit(true)"
            >
              {{ isEdit ? (props.applicant?.status === 'NEEDS_EDIT' ? 'ذخیره و ثبت مجدد' : 'ذخیره و ثبت نهایی') : 'ثبت نهایی' }}
            </Button>
          </template>
        </div>
      </DialogFooter>
    </DialogContent>
  </Dialog>
</template>

<script setup lang="ts">
import { ApiError } from '~/services/backendApi'
import type { LogisticsApplicant } from '~/stores/logistics'
import { MAX_UPLOAD_MB, checkUploadFile } from '~/utils/supplier-form'
import {
  STATUS_LABELS, applicantToForm, blankCoverage, blankLogisticsForm, conflictMessage, conflictStep, formToCreatePayload,
  formToUpdatePayload, mapServerErrors, permitDefsFor, sectionPayload, setAreaType, stepsFor,
  validateLogisticsStep,
} from '~/utils/logistics-form'
import type { ApplicantStatus, ApplicantType, AreaType, StepErrors, StepKey } from '~/utils/logistics-form'

const props = defineProps<{ open: boolean, applicant: LogisticsApplicant | null }>()
const emit = defineEmits<{ 'update:open': [value: boolean], 'saved': [] }>()

const notify = useNotify()
const store = useLogisticsStore()
const PERMIT_ACCEPT = '.pdf,.png,.jpg,.jpeg,.webp'

const allTypeCards = [
  { value: 'COMPANY' as const, title: 'شرکت حمل‌ونقل', text: 'شرکت یا شخصی که ناوگان حمل‌ونقل را مدیریت می‌کند.', icon: 'lucide:building-2' },
  { value: 'DRIVER' as const, title: 'راننده', text: 'راننده‌ای که با خودروی خود بار حمل می‌کند.', icon: 'lucide:truck' },
]
// Only the types the signed-in user may create (the server enforces this too).
const typeCards = computed(() => allTypeCards.filter(c => store.can(c.value, 'create')))

const form = reactive(blankLogisticsForm())
const step = ref(0)
const furthest = ref(0)
const attempted = ref(false)
const saving = ref(false)
const checking = ref(false)
const uploading = ref(false)
const bodyEl = ref<HTMLElement | null>(null)
const serverErrors = ref<StepErrors>({})

const catalog = computed(() => store.reference)
const isEdit = computed(() => !!props.applicant)
const steps = computed(() => stepsFor(form.applicant_type, { withTypeStep: !isEdit.value }))
const currentKey = computed<StepKey>(() => steps.value[step.value]?.key ?? 'type')

watch(() => props.open, async (isOpen) => {
  if (!isOpen) return
  Object.assign(form, props.applicant ? applicantToForm(props.applicant) : blankLogisticsForm())
  serverErrors.value = {}
  step.value = 0
  attempted.value = false
  uploading.value = false
  checking.value = false
  // creating with a single permitted type: no point asking
  if (!props.applicant && typeCards.value.length === 1) form.applicant_type = typeCards.value[0]!.value
  furthest.value = props.applicant ? steps.value.length - 1 : 0 // editing: every step is reachable
  try {
    await store.loadReference()
  }
  catch (e) {
    notify.error(e instanceof ApiError ? e.message : 'بارگذاری فهرست‌های ویزارد انجام نشد.')
  }
}, { immediate: true })

watch(step, () => nextTick(() => bodyEl.value?.scrollTo({ top: 0 })))

// Errors only show after the person tried to continue, then stay live.
const err = computed<StepErrors>(() => attempted.value
  ? { ...validateLogisticsStep(currentKey.value, form, catalog.value), ...serverErrors.value }
  : {})

/* ── type ── */
function chooseType(t: ApplicantType) {
  if (form.applicant_type === t) return
  form.applicant_type = t
  // company and driver answers never mix: the other path's data is dropped
  const fresh = blankLogisticsForm()
  Object.assign(form, { company: fresh.company, rep: fresh.rep, identity: fresh.identity, contact: fresh.contact, vehicle: fresh.vehicle, area: fresh.area })
  furthest.value = 0
}
const canChooseStatus = computed(() => !!form.applicant_type && store.can(form.applicant_type, 'review'))

/* ── provinces / cities ── */
const citiesOf = (province: string) => catalog.value?.provinces.find(p => p.name === province)?.cities ?? []
const cityOptions = (province: string) => citiesOf(province).map(c => ({ code: c, label: c }))
const usedElsewhere = (i: number, name: string) => form.area.coverage.some((c, j) => j !== i && c.province === name)
function changeRowProvince(row: { province: string, all_cities: boolean, cities: string[] }, name: string) {
  if (row.province === name) return
  row.province = name
  row.all_cities = false
  row.cities = [] // the old cities belonged to another province
}
const coverageTitle = computed(() => ({
  CITY: 'شهر محل فعالیت',
  PROVINCIAL: 'استان و شهرهای تحت پوشش',
  INTERPROVINCIAL: 'استان‌ها و شهرهای تحت پوشش',
  INTERNATIONAL: 'استان‌های تحت پوشش (اختیاری)',
} as Record<string, string>)[form.area.area_type] ?? 'پوشش')
const canAddProvince = computed(() => form.area.area_type === 'INTERPROVINCIAL' || form.area.area_type === 'INTERNATIONAL')
const canRemoveProvince = computed(() =>
  form.area.area_type === 'INTERNATIONAL' || (form.area.area_type === 'INTERPROVINCIAL' && form.area.coverage.length > 2))

/* ── permits ── */
const permitDefs = computed(() => permitDefsFor(catalog.value, form.applicant_type))
const permitRow = (code: string) => form.area.permits.find(p => p.type === code)
function togglePermit(code: string, on: boolean) {
  const i = form.area.permits.findIndex(p => p.type === code)
  if (on && i < 0) form.area.permits.push({ type: code, number: '', expires_at: '', file: null })
  if (!on && i >= 0) form.area.permits.splice(i, 1)
}
function setPermitField(code: string, field: 'number' | 'expires_at' | 'file', value: any) {
  const row = permitRow(code)
  if (row) (row as Record<string, any>)[field] = value
}
async function pickPermit(code: string, files: File[]) {
  const file = files[0]
  const row = permitRow(code)
  if (!file || !row) return
  const problem = checkUploadFile(file, PERMIT_ACCEPT)
  if (problem) return notify.error(problem)
  uploading.value = true
  try {
    row.file = await store.uploadFile(file)
  }
  catch (e) {
    notify.error(e instanceof ApiError ? e.message : `بارگذاری فایل «${file.name}» انجام نشد.`)
  }
  finally {
    uploading.value = false
  }
}

/* ── navigation ── */
function goTo(i: number) {
  if (i > furthest.value || i === step.value) return
  if (i > step.value && Object.keys(validateLogisticsStep(currentKey.value, form, catalog.value)).length) {
    attempted.value = true // going forward via the indicator must pass validation too
    return
  }
  attempted.value = false
  serverErrors.value = {}
  step.value = i
}

/** Show the server's complaints and jump to the first step that has one. */
function showServerProblems(e: unknown, fallbackKey: StepKey | null): boolean {
  if (!(e instanceof ApiError)) return false
  if (e.status === 400 && e.code === 'VALIDATION_ERROR') {
    const { errors, step: bad } = mapServerErrors(e.details)
    if (!Object.keys(errors).length) return false
    serverErrors.value = errors
    attempted.value = true
    const idx = steps.value.findIndex(s => s.key === (bad ?? fallbackKey))
    if (idx >= 0) step.value = idx
    return true
  }
  if (e.status === 409) {
    const msg = conflictMessage(e.message)
    const target = fallbackKey ?? conflictStep(e.message, form.applicant_type)
    const field: Partial<Record<StepKey, string>> = {
      identity: 'identity.national_code', contact: 'contact.mobile',
      representative: 'rep.mobile', company_info: 'company.national_id',
    }
    const key = target ? field[target] : undefined
    if (key) serverErrors.value = { [key]: msg }
    const idx = target ? steps.value.findIndex(s => s.key === target) : -1
    if (idx >= 0) step.value = idx
    attempted.value = true
    notify.error(msg)
    return true
  }
  return false
}

async function next() {
  attempted.value = true
  serverErrors.value = {}
  const key = currentKey.value
  if (Object.keys(validateLogisticsStep(key, form, catalog.value)).length) return
  // New records: ask the server about this step now, so duplicates (national code,
  // mobile) show up here and not after the last step. Edits skip it (a record would clash with itself).
  if (!isEdit.value && key !== 'type' && form.applicant_type) {
    checking.value = true
    try {
      await store.validateStep(form.applicant_type, key, sectionPayload(key, form))
    }
    catch (e) {
      if (!showServerProblems(e, key)) notify.error(e instanceof ApiError ? e.message : 'بررسی این مرحله انجام نشد.')
      return
    }
    finally {
      checking.value = false
    }
  }
  attempted.value = false
  step.value++
  furthest.value = Math.max(furthest.value, step.value)
}
function back() {
  attempted.value = false
  serverErrors.value = {}
  step.value--
}

async function submit(finalize = true) {
  // Re-check every step so nothing slips through via the step indicator.
  for (let i = 0; i < steps.value.length; i++) {
    const key = steps.value[i]!.key
    const bad = Object.keys(validateLogisticsStep(key, form, catalog.value))[0]
    if (bad) {
      step.value = i
      attempted.value = true
      notify.error('ابتدا خطاهای مشخص‌شده را برطرف کنید.')
      return
    }
  }
  saving.value = true
  serverErrors.value = {}
  try {
    if (props.applicant) {
      await store.updateApplicant(props.applicant.id, formToUpdatePayload(form))
      if (finalize) await store.finalize(props.applicant.id) // → «در انتظار بررسی»
    }
    else {
      await store.createApplicant(formToCreatePayload(form, finalize))
    }
    notify.success(
      finalize
        ? (props.applicant?.status === 'NEEDS_EDIT' ? 'اطلاعات اصلاح و دوباره برای بررسی ثبت شد.' : 'درخواست ثبت نهایی شد و در صف بررسی قرار گرفت.')
        : isEdit.value ? 'تغییرات ذخیره شد.' : 'پیش‌نویس ذخیره شد؛ تا پیش از ثبت نهایی می‌توانید آن را ویرایش کنید.',
    )
    emit('saved')
    emit('update:open', false)
  }
  catch (e) {
    if (!showServerProblems(e, null)) {
      notify.error(e instanceof ApiError ? requestErrorMessage(e, conflictMessage(e.message)) : 'ذخیره اطلاعات انجام نشد.')
    }
  }
  finally {
    saving.value = false
  }
}
</script>
