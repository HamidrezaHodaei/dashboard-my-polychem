<template>
  <div
    dir="rtl"
    class="space-y-6 text-right"
  >
    <!-- Push: notifications that reach this phone / computer even when the panel is closed -->
    <Card class="shadow-none">
      <CardHeader>
        <CardTitle>اعلان فوری (روی گوشی و رایانه)</CardTitle>
        <CardDescription>
          با فعال‌سازی، اعلان‌های مهم حتی وقتی مرورگر یا برنامه بسته است روی همین دستگاه نمایش داده می‌شود. هر دستگاه را جداگانه فعال کنید.
        </CardDescription>
      </CardHeader>
      <CardContent class="space-y-5">
        <div
          v-if="push.serverEnabled.value === false"
          class="rounded-lg border border-warning/40 bg-muted/30 p-3 text-sm"
          role="status"
        >
          اعلان فوری هنوز روی سرور راه‌اندازی نشده است؛ با مدیر سامانه تماس بگیرید.
        </div>
        <div
          v-else-if="!push.supported.value && !push.needsInstall.value"
          class="rounded-lg border bg-muted/30 p-3 text-sm"
          role="status"
        >
          این مرورگر از اعلان فوری پشتیبانی نمی‌کند. از Chrome، Edge، Firefox یا Safari نسخهٔ جدید استفاده کنید.
        </div>
        <div
          v-else-if="push.needsInstall.value"
          class="rounded-lg border bg-muted/30 p-3 text-sm leading-7"
          role="status"
        >
          روی آیفون و آیپد، اعلان فوری فقط برای برنامه‌ای کار می‌کند که به صفحهٔ اصلی اضافه شده است: در Safari دکمهٔ اشتراک‌گذاری را بزنید، «افزودن به صفحهٔ اصلی» را انتخاب کنید، برنامه را از صفحهٔ اصلی باز کنید و دوباره به همین بخش بیایید.
        </div>
        <template v-else>
          <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <Label>این دستگاه</Label>
              <p class="text-sm text-muted-foreground">
                {{ push.enabledHere.value ? 'اعلان فوری روی این دستگاه فعال است.' : 'اعلان فوری روی این دستگاه فعال نیست.' }}
              </p>
              <p
                v-if="push.blocked.value"
                class="mt-1 text-xs text-destructive"
              >
                مرورگر اجازهٔ اعلان را مسدود کرده است؛ از تنظیمات سایت در مرورگر آن را روی «اجازه» بگذارید.
              </p>
            </div>
            <Button
              v-if="!push.enabledHere.value"
              :disabled="push.busy.value || push.blocked.value"
              @click="enablePush"
            >
              {{ push.busy.value ? 'در حال فعال‌سازی…' : 'فعال‌سازی روی این دستگاه' }}
            </Button>
            <Button
              v-else
              variant="outline"
              :disabled="push.busy.value"
              @click="disablePush"
            >
              غیرفعال‌سازی
            </Button>
          </div>

          <Separator />

          <div>
            <Label>دستگاه‌های شما</Label>
            <ul
              v-if="push.devices.value.length"
              class="mt-2 divide-y rounded-lg border"
            >
              <li
                v-for="d in push.devices.value"
                :key="d.id"
                class="flex flex-col gap-2 p-3 sm:flex-row sm:items-center sm:justify-between"
              >
                <div class="min-w-0">
                  <p class="truncate text-sm font-medium">
                    {{ d.label || 'دستگاه' }}
                    <Badge
                      v-if="d.is_current"
                      variant="secondary"
                      class="me-1 align-middle"
                    >
                      این دستگاه
                    </Badge>
                  </p>
                  <p class="text-xs text-muted-foreground">
                    <template v-if="d.last_success_at">آخرین اعلان موفق: {{ formatNotificationTime(d.last_success_at) }}</template>
                    <template v-else>هنوز اعلانی به این دستگاه ارسال نشده است</template>
                  </p>
                  <p
                    v-if="d.last_error"
                    class="text-xs text-destructive"
                  >
                    آخرین خطا: {{ d.last_error }}
                  </p>
                </div>
                <div class="flex gap-2">
                  <Button
                    size="sm"
                    variant="outline"
                    :disabled="testingId === d.id"
                    @click="testDevice(d.id)"
                  >
                    {{ testingId === d.id ? 'در حال ارسال…' : 'ارسال آزمایشی' }}
                  </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    class="text-destructive hover:text-destructive"
                    @click="removeDevice(d.id)"
                  >
                    حذف
                  </Button>
                </div>
              </li>
            </ul>
            <p
              v-else
              class="mt-1 text-sm text-muted-foreground"
            >
              هنوز دستگاهی ثبت نشده است.
            </p>
          </div>
        </template>
      </CardContent>
    </Card>

    <!-- What to be notified about -->
    <Card
      v-if="prefs"
      class="shadow-none"
    >
      <CardHeader>
        <CardTitle>شخصی‌سازی اعلان‌های فوری</CardTitle>
        <CardDescription>
          این تنظیمات برای همهٔ دستگاه‌های شما اعمال می‌شود. اعلان‌ها همچنان در زنگولهٔ بالای صفحه ثبت می‌شوند.
        </CardDescription>
      </CardHeader>
      <CardContent class="space-y-5">
        <div class="flex items-center justify-between gap-4">
          <div>
            <Label>دریافت اعلان فوری</Label>
            <p class="text-sm text-muted-foreground">
              با خاموش کردن، هیچ اعلان فوری ارسال نمی‌شود.
            </p>
          </div>
          <Switch
            dir="ltr"
            :model-value="prefs.push_enabled"
            aria-label="دریافت اعلان فوری"
            @update:model-value="v => (prefs!.push_enabled = !!v)"
          />
        </div>

        <Separator />

        <div class="flex items-center justify-between gap-4">
          <div>
            <Label>نمایش متن اعلان روی صفحهٔ قفل</Label>
            <p class="text-sm text-muted-foreground">
              اگر خاموش باشد فقط «اعلان جدید در پلیکم» نمایش داده می‌شود و متن آن پس از ورود دیده می‌شود.
            </p>
          </div>
          <Switch
            dir="ltr"
            :model-value="prefs.show_preview"
            aria-label="نمایش متن اعلان"
            @update:model-value="v => (prefs!.show_preview = !!v)"
          />
        </div>

        <Separator />

        <div class="space-y-3">
          <div class="flex items-center justify-between gap-4">
            <div>
              <Label>ساعات سکوت</Label>
              <p class="text-sm text-muted-foreground">
                در این بازه اعلان فوری ارسال نمی‌شود و بعد از پایان آن یک‌جا می‌رسد (به وقت تهران).
              </p>
            </div>
            <Switch
              dir="ltr"
              :model-value="prefs.quiet_enabled"
              aria-label="ساعات سکوت"
              @update:model-value="v => (prefs!.quiet_enabled = !!v)"
            />
          </div>
          <div
            v-if="prefs.quiet_enabled"
            class="flex flex-wrap items-center gap-3"
          >
            <Label
              for="quiet-start"
              class="text-sm"
            >از</Label>
            <Input
              id="quiet-start"
              v-model="prefs.quiet_start"
              type="time"
              dir="ltr"
              class="w-32"
            />
            <Label
              for="quiet-end"
              class="text-sm"
            >تا</Label>
            <Input
              id="quiet-end"
              v-model="prefs.quiet_end"
              type="time"
              dir="ltr"
              class="w-32"
            />
          </div>
        </div>

        <Separator />

        <div>
          <Label>دسته‌های اعلان</Label>
          <ul class="mt-2 divide-y rounded-lg border">
            <li
              v-for="c in prefs.categories"
              :key="c.key"
              class="flex items-center justify-between gap-4 p-3"
            >
              <div>
                <p class="text-sm font-medium">
                  {{ c.label }}
                </p>
                <p class="text-xs text-muted-foreground">
                  {{ c.description }}
                </p>
              </div>
              <Switch
                dir="ltr"
                :model-value="c.push_enabled"
                :aria-label="c.label"
                @update:model-value="v => (c.push_enabled = !!v)"
              />
            </li>
          </ul>
        </div>

        <div class="flex justify-end">
          <Button
            :disabled="saving"
            @click="savePrefs"
          >
            {{ saving ? 'در حال ذخیره…' : 'ذخیرهٔ تنظیمات' }}
          </Button>
        </div>
      </CardContent>
    </Card>

    <Card class="shadow-none">
      <CardHeader>
        <CardTitle>اعلان‌ها</CardTitle>
        <CardDescription>
          اعلان امور محوله جدید، ارجاع، منشن و نزدیک شدن یا گذشتن موعد در زنگوله‌ی بالای صفحه نمایش داده می‌شود. این تنظیمات فقط روی همین مرورگر اعمال می‌شود.
        </CardDescription>
      </CardHeader>
      <CardContent class="space-y-5">
        <div class="flex items-center justify-between gap-4">
          <div>
            <Label>صدای اعلان</Label>
            <p class="text-sm text-muted-foreground">
              هنگام رسیدن اعلان جدید (مثلاً امور محوله تازه) یک صدای کوتاه پخش می‌شود.
            </p>
          </div>
          <div class="flex items-center gap-3">
            <Button
              type="button"
              variant="outline"
              size="sm"
              class="gap-1.5"
              @click="store.playSound()"
            >
              آزمایش صدا
            </Button>
            <Switch
              dir="ltr"
              :model-value="store.sound"
              aria-label="صدای اعلان"
              @update:model-value="v => store.setSound(!!v)"
            />
          </div>
        </div>

        <Separator />

        <div class="flex items-center justify-between gap-4">
          <div>
            <Label>اعلان سیستم (وقتی برنامه در پس‌زمینه است)</Label>
            <p class="text-sm text-muted-foreground">
              با اجازه‌ی مرورگر، اعلان روی دسکتاپ نمایش داده می‌شود.
            </p>
            <p
              v-if="blocked"
              class="mt-1 text-xs text-destructive"
            >
              مرورگر اجازه‌ی اعلان را مسدود کرده است؛ از تنظیمات سایت در مرورگر آن را فعال کنید.
            </p>
          </div>
          <Switch
            dir="ltr"
            :model-value="store.desktop"
            :disabled="!supported"
            aria-label="اعلان سیستم"
            @update:model-value="toggleDesktop"
          />
        </div>

        <Separator />

        <div class="rounded-lg border bg-muted/20 p-4 text-sm leading-7 text-muted-foreground">
          <p class="font-medium text-foreground">
            چه چیزهایی اعلان می‌شود؟
          </p>
          <ul class="mt-1 list-disc space-y-1 pr-5">
            <li>امور محوله جدیدی که برای شما تعریف یا به شما ارجاع می‌شود</li>
            <li>منشن‌شدن شما در پیام‌های یک امور محوله</li>
            <li>کمتر از ۲۴ ساعت مانده به موعد امور محوله شما، و اموری که موعدشان گذشته است</li>
            <li>نتیجه‌ی بررسی درخواست‌های ثبت‌شده (تأیید، رد یا نیاز به ویرایش)</li>
            <li>مراحل درخواست‌های خرید: ثبت جدید، تأیید مدیر، پرداخت، حمل و تحویل</li>
            <li>مراحل درخواست نمونه و یادآوری پیگیری مشتری</li>
          </ul>
        </div>
      </CardContent>
    </Card>
  </div>
</template>

<script lang="ts" setup>
usePageSeoMeta({ title: 'اعلان‌ها' })
import type { PushPreferences } from '~/composables/usePush'
import { ApiError, apiFetch } from '~/services/backendApi'

const store = useNotificationsStore()
const notify = useNotify()
const push = usePush()
const prefs = ref<PushPreferences | null>(null)
const saving = ref(false)
const testingId = ref<number | null>(null)

onMounted(async () => {
  store.loadPrefs()
  await push.refreshState()
  try { prefs.value = await apiFetch<PushPreferences>('/notifications/preferences') }
  catch { /* offline: the personalisation card simply stays hidden */ }
})

async function enablePush() {
  const r = await push.enable()
  if (!r.ok && r.message) notify.error(r.message)
  else if (r.ok) notify.success('اعلان فوری روی این دستگاه فعال شد')
}
async function disablePush() {
  await push.disable()
  notify.info('اعلان فوری روی این دستگاه غیرفعال شد')
}
async function testDevice(id: number) {
  testingId.value = id
  try {
    const r = await push.testDevice(id)
    if (r.ok) notify.success('اعلان آزمایشی ارسال شد')
    else notify.error(r.error || 'ارسال انجام نشد')
  }
  catch { notify.error('ارسال انجام نشد') }
  finally { testingId.value = null }
}
async function removeDevice(id: number) {
  try { await push.removeDevice(id) }
  catch { notify.error('حذف دستگاه انجام نشد') }
}
async function savePrefs() {
  if (!prefs.value) return
  saving.value = true
  try {
    const p = prefs.value
    prefs.value = await apiFetch<PushPreferences>('/notifications/preferences', {
      method: 'PUT',
      body: {
        push_enabled: p.push_enabled, show_preview: p.show_preview, quiet_enabled: p.quiet_enabled,
        quiet_start: p.quiet_start, quiet_end: p.quiet_end,
        categories: Object.fromEntries(p.categories.map(c => [c.key, c.push_enabled])),
      },
    })
    notify.success('تنظیمات ذخیره شد')
  }
  catch (e) { notify.error(e instanceof ApiError ? e.message : 'ذخیره انجام نشد') }
  finally { saving.value = false }
}

const supported = computed(() => import.meta.client && 'Notification' in window)
const blocked = computed(() => import.meta.client && 'Notification' in window && Notification.permission === 'denied')

async function toggleDesktop(on: boolean | string) {
  const ok = await store.setDesktop(!!on)
  if (!ok) notify.error('اجازه‌ی اعلان از طرف مرورگر داده نشد')
}
</script>
