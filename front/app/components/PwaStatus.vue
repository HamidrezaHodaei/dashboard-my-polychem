<template>
  <div
    class="pointer-events-none fixed inset-x-0 z-[100] flex flex-col items-center gap-2 px-3"
    style="top: calc(env(safe-area-inset-top, 0px) + 0.5rem)"
  >
    <!-- Offline: the panel needs the API, so say so plainly instead of letting requests fail one by one. -->
    <div
      v-if="!online"
      role="status"
      aria-live="polite"
      class="pointer-events-auto w-full max-w-md rounded-lg border border-warning/40 bg-popover px-4 py-2.5 text-center text-sm text-popover-foreground"
    >
      اتصال اینترنت برقرار نیست. تغییرات جدید تا بازگشت اتصال ذخیره نمی‌شوند.
    </div>

    <div
      v-if="updateReady"
      role="status"
      class="pointer-events-auto flex w-full max-w-md items-center justify-between gap-3 rounded-lg border bg-popover px-4 py-2.5 text-sm text-popover-foreground"
    >
      <span>نسخه جدید سامانه آماده است.</span>
      <Button
        size="sm"
        @click="applyUpdate"
      >
        به‌روزرسانی
      </Button>
    </div>
  </div>

  <!-- Install suggestion: bottom sheet-like card, dismissible for 14 days, never shown inside the installed app. -->
  <div
    v-if="(canInstall || showIosHint) && route.path !== '/install'"
    class="fixed inset-x-0 z-[100] flex justify-center px-3"
    style="bottom: calc(env(safe-area-inset-bottom, 0px) + 0.75rem)"
  >
    <div
      role="dialog"
      aria-label="نصب سامانه"
      class="w-full max-w-md rounded-lg border bg-popover p-4 text-popover-foreground"
    >
      <p class="text-sm font-semibold">
        نصب سامانه پلیکم
      </p>
      <p class="mt-1 text-sm leading-7 text-muted-foreground">
        <template v-if="canInstall">
          سامانه را مانند یک برنامه روی این دستگاه نصب کنید تا سریع‌تر و بدون نوار آدرس مرورگر باز شود.
        </template>
        <template v-else>
          در Safari دکمه اشتراک‌گذاری را بزنید و گزینه «افزودن به صفحه اصلی» را انتخاب کنید.
        </template>
      </p>
      <div class="mt-3 flex justify-end gap-2">
        <Button
          variant="ghost"
          size="sm"
          @click="dismissInstall"
        >
          بعداً
        </Button>
        <Button
          v-if="canInstall"
          size="sm"
          @click="install"
        >
          نصب
        </Button>
      </div>
    </div>
  </div>
</template>

<script lang="ts" setup>
import { Button } from '@/components/ui/button'

const route = useRoute()
const { online, canInstall, showIosHint, updateReady, applyUpdate, install, dismissInstall } = usePwa()
</script>
