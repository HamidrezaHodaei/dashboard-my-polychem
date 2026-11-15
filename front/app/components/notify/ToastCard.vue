<script lang="ts" setup>
import { ChevronDownIcon, CircleCheckIcon, InfoIcon, OctagonXIcon, TriangleAlertIcon, XIcon } from '@lucide/vue'
import { toast } from 'vue-sonner'

type Tone = 'success' | 'error' | 'warning' | 'info'

const props = defineProps<{
  id: string | number
  tone: Tone
  title: string
  description?: string
  duration?: number
  action?: { label: string, onClick?: () => void }
}>()

const TICK = 100
const total = props.duration ?? 4000
const remaining = ref(total)
const paused = ref(false)
const open = ref(false)
let timer: ReturnType<typeof setInterval> | null = null

// «مشاهده بیشتر»: عنوان در حالت بسته حداکثر دو خط نمایش داده می‌شود؛ اگر واقعاً بریده شده باشد
// (با اندازه‌گیری DOM، نه حدس روی تعداد حروف) دکمه‌ی مشاهده‌ی کامل متن نشان داده می‌شود.
const titleEl = ref<HTMLElement | null>(null)
const titleClipped = ref(false)
let resizeObserver: ResizeObserver | null = null

function measureTitle() {
  const el = titleEl.value
  if (!el || open.value) return
  titleClipped.value = el.scrollHeight > el.clientHeight + 1
}

const hasBody = computed(() => !!(props.description || props.action))
const expandable = computed(() => hasBody.value || titleClipped.value)
const progress = computed(() => (remaining.value / total) * 100)
const secondsLeft = computed(() => Math.ceil(remaining.value / 1000).toLocaleString('fa-IR'))

const themes = {
  success: { icon: CircleCheckIcon, text: 'text-emerald-500', bar: 'bg-emerald-500' },
  error: { icon: OctagonXIcon, text: 'text-red-500', bar: 'bg-red-500' },
  warning: { icon: TriangleAlertIcon, text: 'text-amber-500', bar: 'bg-amber-400' },
  info: { icon: InfoIcon, text: 'text-sky-500', bar: 'bg-sky-500' },
} as const
const theme = computed(() => themes[props.tone] ?? themes.info)

function close() {
  toast.dismiss(props.id)
}

function runAction() {
  props.action?.onClick?.()
  close()
}

// تا وقتی کاربر در حال خواندن متن کامل است، تایمر بسته شدن متوقف می‌ماند.
function toggle() {
  open.value = !open.value
  if (open.value) paused.value = true
  else nextTick(measureTitle)
}

onMounted(() => {
  timer = setInterval(() => {
    if (paused.value) return
    remaining.value -= TICK
    if (remaining.value <= 0) close()
  }, TICK)

  nextTick(measureTitle)
  if (typeof ResizeObserver !== 'undefined' && titleEl.value) {
    resizeObserver = new ResizeObserver(measureTitle)
    resizeObserver.observe(titleEl.value)
  }
})

onBeforeUnmount(() => {
  if (timer) clearInterval(timer)
  resizeObserver?.disconnect()
})
</script>

<template>
  <div
    dir="rtl"
    class="w-full min-w-0 max-w-[calc(100vw-2rem)] overflow-hidden rounded-lg border border-border bg-popover text-right text-popover-foreground shadow-lg sm:w-[22rem]"
  >
    <!-- سربرگ -->
    <div class="flex items-start gap-2.5 px-3.5 pt-3 pb-2.5">
      <component :is="theme.icon" class="mt-0.5 size-5 shrink-0" :class="theme.text" />
      <p
        ref="titleEl"
        class="min-w-0 flex-1 whitespace-pre-line text-sm font-semibold leading-6 [overflow-wrap:anywhere]"
        :class="open ? '' : 'line-clamp-2'"
      >
        {{ title }}
      </p>

      <button
        v-if="expandable"
        type="button"
        class="mt-0.5 shrink-0 rounded p-1 text-muted-foreground transition hover:bg-muted hover:text-foreground"
        :aria-label="open ? 'مشاهده کمتر' : 'مشاهده بیشتر'"
        :aria-expanded="open"
        @click="toggle"
      >
        <ChevronDownIcon class="size-4 transition-transform duration-300" :class="open ? 'rotate-180' : ''" />
      </button>
      <button
        type="button"
        class="mt-0.5 shrink-0 rounded p-1 text-muted-foreground transition hover:bg-muted hover:text-foreground"
        aria-label="بستن"
        @click="close"
      >
        <XIcon class="size-4" />
      </button>
    </div>

    <!-- بدنه‌ی قابل باز شدن -->
    <div
      v-if="hasBody"
      class="grid transition-[grid-template-rows] duration-300 ease-out"
      :class="open ? 'grid-rows-[1fr]' : 'grid-rows-[0fr]'"
    >
      <div class="overflow-hidden">
        <div class="max-h-[45vh] overflow-y-auto px-3.5 pb-3.5 pt-0.5">
          <p
            v-if="description"
            class="whitespace-pre-line text-[13px] leading-6 text-muted-foreground [overflow-wrap:anywhere]"
          >
            {{ description }}
          </p>
          <button
            v-if="action"
            type="button"
            class="mt-3 rounded-md border border-border bg-background px-3 py-1.5 text-[13px] font-medium shadow-sm transition hover:bg-muted active:scale-95"
            @click="runAction"
          >
            {{ action.label }}
          </button>
        </div>
      </div>
    </div>

    <!-- مشاهده‌ی بیشتر برای عنوان بلندِ بدون توضیح -->
    <button
      v-if="expandable && !hasBody"
      type="button"
      class="block w-full px-3.5 pb-2 text-start text-[11px] font-medium text-primary hover:underline"
      :aria-expanded="open"
      @click="toggle"
    >
      {{ open ? 'مشاهده کمتر' : 'مشاهده بیشتر' }}
    </button>

    <!-- فوتر تایمر -->
    <button
      type="button"
      class="block w-full bg-muted/50 px-3.5 py-1.5 text-start text-[11px] text-muted-foreground"
      @click="paused = !paused"
    >
      <template v-if="paused">
        <span class="font-medium text-foreground">متوقف شد.</span> برای ادامه کلیک کنید.
      </template>
      <template v-else>
        این پیام تا <span class="font-medium text-foreground">{{ secondsLeft }}</span> ثانیه دیگر بسته می‌شود.
        <span class="font-medium text-foreground">برای توقف کلیک کنید.</span>
      </template>
    </button>

    <!-- نوار پیشرفت -->
    <div class="h-[3px] w-full">
      <div
        class="h-full transition-[width] duration-100 ease-linear"
        :class="theme.bar"
        :style="{ width: `${progress}%` }"
      />
    </div>
  </div>
</template>
