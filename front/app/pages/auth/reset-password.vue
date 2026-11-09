<template>
  <AuthTemplate>
    <template v-if="!submitted">
      <div
        class="flex flex-col justify-center space-y-6"
      >
        <div class="space-y-1 text-center">
          <h1 class="text-2xl font-semibold leading-none tracking-tight">
            رمز عبور خود را فراموش کرده‌اید؟
          </h1>
          <p class="mt-1 text-muted-foreground">
            برای بازنشانی رمز عبور، ایمیل خود را وارد کنید
          </p>
        </div>

        <form
          @submit="onSubmit"
        >
          <div class="space-y-3">
            <FormField
              v-slot="{ componentField }"
              name="email"
            >
              <FormItem>
                <FormLabel>ایمیل</FormLabel>
                <FormControl>
                  <Input
                    type="email"
                    placeholder="ایمیل خود را وارد کنید"
                    autocomplete="off"
                    v-bind="componentField"
                  />
                </FormControl>
                <FormMessage />
              </FormItem>
            </FormField>
          </div>
          <div class="mt-6">
            <Button
              class="w-full"
              type="submit"
            >
              ارسال پیوند بازنشانی
            </Button>
          </div>
        </form>

        <div class="px-6 space-y-2 text-center">
          <p class="text-sm font-medium">
            از قبل حساب کاربری دارید؟
            <NuxtLink
              to="/auth/signin"
              class="hover:underline text-primary-content"
            >
              ورود
            </NuxtLink>
          </p>
          <p class="text-sm font-medium">
            حساب کاربری ندارید؟
            <NuxtLink
              to="/auth/signup"
              class="hover:underline text-primary-content"
            >
              ایجاد حساب کاربری
            </NuxtLink>
          </p>
        </div>
      </div>
    </template>
    <template v-else>
      <div class="space-y-1">
        <h1 class="text-2xl font-semibold leading-none tracking-tight">
          پیوند بازنشانی رمز عبور ارسال شد
        </h1>
        <p class="mt-2 text-sm text-muted-foreground">
          پیوند بازنشانی رمز عبور به ایمیل شما ارسال شد. لطفاً دستورالعمل‌های ارسال‌شده را دنبال کنید.
        </p>
      </div>
    </template>
  </AuthTemplate>
</template>

<script lang="ts" setup>
import { useForm } from 'vee-validate'
import { toTypedSchema } from '@vee-validate/zod'
import * as z from 'zod'
const notify = useNotify()

definePageMeta({
  layout: 'blank',
  // for demonstration purpose we use public instead of guest
  public: true,
})

const submitted = ref(false)

const formSchema = toTypedSchema(
  z
    .object({
      email: z.string().email(),
    }),
)

const { handleSubmit } = useForm({
  validationSchema: formSchema,
})

const onSubmit = handleSubmit((values) => {
  console.log('handle RESET password', values)
  submitted.value = true
  toast('ایمیل بازنشانی رمز عبور ارسال شد.')
})
</script>
