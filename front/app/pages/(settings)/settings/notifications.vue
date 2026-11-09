<template>
  <div
    dir="rtl"
    class="space-y-6 text-right"
  >
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
              <Icon
                name="lucide:volume-2"
                class="size-4"
              /> آزمایش صدا
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
          </ul>
        </div>
      </CardContent>
    </Card>
  </div>
</template>

<script lang="ts" setup>
usePageSeoMeta({ title: 'اعلان‌ها' })

const store = useNotificationsStore()
const notify = useNotify()
onMounted(() => store.loadPrefs())

const supported = computed(() => import.meta.client && 'Notification' in window)
const blocked = computed(() => import.meta.client && 'Notification' in window && Notification.permission === 'denied')

async function toggleDesktop(on: boolean | string) {
  const ok = await store.setDesktop(!!on)
  if (!ok) notify.error('اجازه‌ی اعلان از طرف مرورگر داده نشد')
}
</script>
