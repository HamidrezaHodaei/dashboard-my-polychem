<template>
  <div
    dir="rtl"
    class="space-y-6 text-right"
  >
    <Card class="shadow-none">
      <CardHeader>
        <CardTitle>تغییر رمز عبور</CardTitle>
        <CardDescription>
          با تغییر رمز، از سایر دستگاه‌ها خارج می‌شوید و نشست فعلی شما باقی می‌ماند.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form
          class="max-w-md space-y-4"
          @submit.prevent="submit"
        >
          <div class="space-y-1.5">
            <Label for="current-password">رمز عبور فعلی</Label>
            <Input
              id="current-password"
              v-model="form.current"
              type="password"
              dir="ltr"
              class="text-left"
              autocomplete="current-password"
              :aria-invalid="!!errors.current"
            />
            <p
              v-if="errors.current"
              class="text-xs text-destructive"
            >
              {{ errors.current }}
            </p>
          </div>
          <div class="space-y-1.5">
            <Label for="new-password">رمز عبور جدید</Label>
            <Input
              id="new-password"
              v-model="form.next"
              type="password"
              dir="ltr"
              class="text-left"
              autocomplete="new-password"
              :aria-invalid="!!errors.next"
            />
            <p
              v-if="errors.next"
              class="text-xs text-destructive"
            >
              {{ errors.next }}
            </p>
            <p
              v-else
              class="text-xs text-muted-foreground"
            >
              حداقل ۸ نویسه؛ ترکیبی از حروف، عدد و نشانه امن‌تر است.
            </p>
          </div>
          <div class="space-y-1.5">
            <Label for="confirm-password">تکرار رمز عبور جدید</Label>
            <Input
              id="confirm-password"
              v-model="form.confirm"
              type="password"
              dir="ltr"
              class="text-left"
              autocomplete="new-password"
              :aria-invalid="!!errors.confirm"
            />
            <p
              v-if="errors.confirm"
              class="text-xs text-destructive"
            >
              {{ errors.confirm }}
            </p>
          </div>
          <Button
            type="submit"
            class="gap-2"
            :disabled="saving"
          >
            <Icon
              name="lucide:key-round"
              class="size-4"
            />
            {{ saving ? 'در حال ذخیره...' : 'ذخیره‌ی رمز جدید' }}
          </Button>
        </form>
      </CardContent>
    </Card>

    <Card class="shadow-none">
      <CardHeader>
        <CardTitle>اطلاعات امنیتی حساب</CardTitle>
        <CardDescription>رمز عبور هیچ‌کس، حتی مدیر سیستم، قابل مشاهده نیست؛ فقط می‌توان رمز جدید تعیین کرد.</CardDescription>
      </CardHeader>
      <CardContent class="space-y-2 text-sm">
        <div class="flex items-center justify-between rounded-lg border bg-muted/20 px-3 py-2.5">
          <span class="text-muted-foreground">آخرین ورود</span>
          <span>{{ auth.user?.last_login_at ? formatTehranDateTime(auth.user.last_login_at) : '—' }}</span>
        </div>
        <p class="text-xs text-muted-foreground">
          اگر رمز خود را فراموش کرده‌اید، مدیر سیستم می‌تواند از بخش «مدیریت دسترسی ← کاربران» رمز جدیدی برای شما تعیین کند.
        </p>
      </CardContent>
    </Card>
  </div>
</template>

<script lang="ts" setup>
import { ApiError } from '~/services/backendApi'

usePageSeoMeta({ title: 'امنیت' })

const auth = useAuthStore()
const notify = useNotify()
const form = reactive({ current: '', next: '', confirm: '' })
const errors = reactive({ current: '', next: '', confirm: '' })
const saving = ref(false)

async function submit() {
  Object.assign(errors, { current: '', next: '', confirm: '' })
  if (!form.current) errors.current = 'رمز عبور فعلی را وارد کنید.'
  if (form.next.length < 8) errors.next = 'رمز عبور جدید باید حداقل ۸ نویسه باشد.'
  else if (form.next === form.current) errors.next = 'رمز جدید باید با رمز فعلی متفاوت باشد.'
  if (form.confirm !== form.next) errors.confirm = 'تکرار رمز با رمز جدید یکسان نیست.'
  if (errors.current || errors.next || errors.confirm) return
  saving.value = true
  try {
    await auth.changePassword(form.current, form.next)
    Object.assign(form, { current: '', next: '', confirm: '' })
    notify.success('رمز عبور شما تغییر کرد')
  }
  catch (err) {
    if (err instanceof ApiError && err.status === 409 && /current password/i.test(err.message)) errors.current = 'رمز عبور فعلی درست نیست.'
    else if (err instanceof ApiError && err.status === 409) errors.next = 'رمز جدید باید با رمز فعلی متفاوت باشد.'
    else notify.error('تغییر رمز انجام نشد؛ دوباره تلاش کنید')
  }
  finally {
    saving.value = false
  }
}
</script>
