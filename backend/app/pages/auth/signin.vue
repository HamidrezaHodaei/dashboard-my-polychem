<template>
  <div class="relative grid min-h-dvh w-full overflow-hidden bg-background text-foreground lg:grid-cols-[1.1fr_1fr]">
    <!-- پس‌زمینه نقطه‌ای تعاملی (پشت کل صفحه) -->
    <InteractiveDots class="z-0" />

    <!-- ستون فرم (در RTL سمت راست) -->
    <div class="relative z-10 flex flex-col px-5 py-5 sm:px-10 lg:px-16">
      <div class="flex h-12 items-center justify-start">
        <ColorModeButton />
      </div>

      <div class="flex flex-1 items-center justify-center py-8">
        <div class="w-full max-w-md space-y-8">
          <div class="space-y-3 text-start">
            <h1
              class="grid text-5xl font-extrabold leading-tight text-[#878787] sm:text-6xl xl:text-7xl dark:text-neutral-400"
              translate="no"
              aria-label="پلیکم من"
            >
              <!-- نسخه نامرئی برای ثابت ماندن ابعاد -->
              <span
                class="invisible col-start-1 row-start-1"
                aria-hidden="true"
              >پلیکم من</span>
              <span
                class="col-start-1 row-start-1"
                aria-hidden="true"
              >
                <span v-text="typed" />
                <span class="caret" />
              </span>
            </h1>
            <p class="text-sm sm:text-base">
              یک تجربه یکپارچه، برای همکاری بهتر و پیشرفت بیشتر.
            </p>
          </div>

          <form
            class="text-start"
            novalidate
            @submit="onSubmit"
          >
            <div class="space-y-4">
              <FormField
                v-slot="{ componentField }"
                name="email"
              >
                <FormItem>
                  <FormControl>
                    <div class="relative">
                      <Icon
                        name="lucide:user"
                        class="pointer-events-none absolute start-4 top-1/2 size-6 -translate-y-1/2"
                        aria-hidden="true"
                      />
                      <Input
                        type="email"
                        dir="ltr"
                        placeholder="ایمیل"
                        autocomplete="email"
                        class="h-14 rounded-2xl border border-[#dcdcdc] !bg-[#ececec] pl-4 pr-14 text-right text-base shadow-none focus-visible:ring-2 focus-visible:ring-[#fdd00a]/60 dark:border-white/10 dark:!bg-white/10"
                        v-bind="componentField"
                      />
                    </div>
                  </FormControl>
                  <FormMessage />
                </FormItem>
              </FormField>

              <FormField
                v-slot="{ componentField }"
                name="password"
              >
                <FormItem>
                  <FormControl>
                    <div class="relative">
                      <Icon
                        name="lucide:lock-keyhole"
                        class="pointer-events-none absolute start-4 top-1/2 size-6 -translate-y-1/2"
                        aria-hidden="true"
                      />
                      <Input
                        :type="showPassword ? 'text' : 'password'"
                        placeholder="رمز عبور"
                        autocomplete="current-password"
                        class="h-14 rounded-2xl border border-[#dcdcdc] !bg-[#ececec] pe-12 ps-14 text-base shadow-none focus-visible:ring-2 focus-visible:ring-[#fdd00a]/60 dark:border-white/10 dark:!bg-white/10"
                        v-bind="componentField"
                      />
                      <button
                        type="button"
                        class="absolute end-4 top-1/2 -translate-y-1/2 text-muted-foreground transition-colors hover:text-foreground"
                        :aria-label="showPassword ? 'مخفی کردن رمز عبور' : 'نمایش رمز عبور'"
                        @click="showPassword = !showPassword"
                      >
                        <Icon
                          :name="showPassword ? 'lucide:eye-off' : 'lucide:eye'"
                          class="size-5"
                          aria-hidden="true"
                        />
                      </button>
                    </div>
                  </FormControl>
                  <FormMessage />
                </FormItem>
              </FormField>
            </div>

            <div class="mt-5 text-sm">
              <NuxtLink
                to="/auth/reset-password"
                class="text-[#fdd00a] hover:underline"
              >
                رمز عبور خود را فراموش کرده‌اید؟
              </NuxtLink>
            </div>

            <div class="mt-6 text-[#848484]">
              <LoginButton
                type="submit"
                :disabled="isSubmitting || isLoading"
                :loading="isLoading"
              >
                ورود
              </LoginButton>
            </div>
          </form>
        </div>
      </div>
    </div>

    <!-- ستون تصویر (در RTL سمت چپ) - فقط از lg به بالا -->
    <div class="relative z-10 hidden p-4 lg:block xl:p-6">
      <div class="relative h-full w-full overflow-hidden rounded-[2.5rem]">
        <img
          :src="heroImage"
          alt=""
          class="absolute inset-0 h-full w-full object-cover dark:brightness-90"
        >
      </div>
    </div>
  </div>
</template>

<script lang="ts" setup>
import { useForm } from 'vee-validate'
import { toTypedSchema } from '@vee-validate/zod'
import * as z from 'zod'
const notify = useNotify()
import { ApiError } from '~/services/backendApi'

useHead({
  title: 'پلیکم من',
  titleTemplate: '%s',
})

definePageMeta({
  layout: 'blank',
  // for demonstration purpose we use public instead of guest
  public: true,
})

const heroImage = '/login.webp'

// ---------- انیمیشن تایپ عنوان ----------
const fullTitle = 'پلیکم من'
const typed = ref('')
let typingTimer: ReturnType<typeof setTimeout> | undefined

onMounted(() => {
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    typed.value = fullTitle
    return
  }

  const chars = Array.from(fullTitle)
  let index = 0
  let deleting = false

  const step = () => {
    if (!deleting) {
      index++
      typed.value = chars.slice(0, index).join('')
      if (index === chars.length) {
        deleting = true
        typingTimer = setTimeout(step, 2200)
        return
      }
      typingTimer = setTimeout(step, 170)
    }
    else {
      index--
      typed.value = chars.slice(0, index).join('')
      if (index === 0) {
        deleting = false
        typingTimer = setTimeout(step, 600)
        return
      }
      typingTimer = setTimeout(step, 90)
    }
  }

  typingTimer = setTimeout(step, 400)
})

onBeforeUnmount(() => {
  if (typingTimer) clearTimeout(typingTimer)
})

// ---------- لاگین (بدون تغییر) ----------
const { login } = useAuth()

const testUser = {
  email: '',
  password: '',
}

const isLoading = ref(false)
const showPassword = ref(false)

const formSchema = toTypedSchema(
  z
    .object({
      email: z.string().email('لطفاً یک نشانی ایمیل معتبر وارد کنید.'),
      password: z.string().min(8, 'رمز عبور باید دست‌کم ۸ نویسه باشد.'),
    }),
)

const route = useRoute()
const { isSubmitting, handleSubmit } = useForm({
  validationSchema: formSchema,
  initialValues: testUser,
})

const onSubmit = handleSubmit(async (values) => {
  isLoading.value = true
  try {
    await login({ email: values.email, password: values.password })
    const target = route.query.redirect
    await navigateTo(typeof target === 'string' && target.startsWith('/') && !target.startsWith('//') ? target : '/')
  }
  catch (error: unknown) {
    console.error(error)
    isLoading.value = false
    notify.error(getLoginErrorMessage(error))
  }
})

function getLoginErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 401) {
      return 'ایمیل یا رمز عبور نادرست است.'
    }

    if (error.code === 'NETWORK_ERROR' || error.status === 0) {
      return 'ارتباط با سرور برقرار نشد. لطفاً اتصال اینترنت خود را بررسی کنید.'
    }

    if (error.status === 403) {
      return 'شما اجازهٔ ورود به سامانه را ندارید.'
    }

    if (error.status === 429) {
      return 'تعداد تلاش‌های ورود بیش از حد مجاز است. لطفاً کمی بعد دوباره تلاش کنید.'
    }
  }

  return 'ورود به سامانه با مشکل روبه‌رو شد. لطفاً دوباره تلاش کنید.'
}
</script>

<style scoped>
.caret {
  display: inline-block;
  width: 4px;
  height: 0.85em;
  margin-inline-start: 6px;
  vertical-align: middle;
  background-color: #fdd00a;
  border-radius: 2px;
  animation: caret-blink 1s steps(1) infinite;
}

@keyframes caret-blink {
  0%, 50% { opacity: 1; }
  50.01%, 100% { opacity: 0; }
}
</style>