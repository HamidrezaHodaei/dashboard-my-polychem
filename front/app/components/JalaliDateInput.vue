<!-- /components/JalaliDateInput.vue  → <JalaliDateInput v-model="isoDate" :max="todayIso()" /> -->
<!--
  Shamsi (Jalali) date field. The model is a Gregorian ISO string
  ("YYYY-MM-DD", what the API stores) or ''. The person sees and types
  Jalali ("۱۴۰۴/۰۱/۰۱"). The calendar opens *inline* under the field (not in a
  floating layer) so it can't be clipped by the dialog's scroll area.
-->
<template>
  <div
    ref="root"
    class="space-y-2"
    dir="rtl"
  >
    <div class="relative">
      <Input
        v-model="text"
        dir="ltr"
        class="pl-10 text-right"
        inputmode="numeric"
        placeholder="۱۴۰۴/۰۱/۰۱"
        maxlength="10"
        :disabled="disabled"
        :aria-invalid="invalid || !!typedError"
        @blur="commitText"
        @keydown.enter.prevent="commitText"
        @keydown.esc="panel = false"
      />
      <button
        type="button"
        class="absolute left-2 top-1/2 -translate-y-1/2 rounded p-1 text-muted-foreground hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-50"
        aria-label="باز کردن تقویم"
        :disabled="disabled"
        @click="togglePanel"
      >
        <Icon
          name="lucide:calendar"
          class="size-4"
        />
      </button>
    </div>
    <p
      v-if="typedError"
      class="text-xs text-destructive"
    >
      {{ typedError }}
    </p>

    <div
      v-if="panel"
      class="w-full max-w-72 rounded-lg border bg-background p-3 shadow-sm"
    >
      <div class="mb-2 flex items-center gap-1">
        <Button
          type="button"
          variant="ghost"
          size="icon"
          class="size-7"
          aria-label="ماه قبل"
          @click="shiftMonth(-1)"
        >
          <Icon
            name="lucide:chevron-right"
            class="size-4"
          />
        </Button>
        <select
          v-model.number="viewMonth"
          class="h-7 flex-1 rounded-md border bg-background px-1 text-sm"
          aria-label="ماه"
        >
          <option
            v-for="(m, i) in JALALI_MONTHS"
            :key="m"
            :value="i + 1"
          >
            {{ m }}
          </option>
        </select>
        <select
          v-model.number="viewYear"
          class="h-7 w-20 rounded-md border bg-background px-1 text-sm"
          aria-label="سال"
        >
          <option
            v-for="y in years"
            :key="y"
            :value="y"
          >
            {{ toPersianDigits(y) }}
          </option>
        </select>
        <Button
          type="button"
          variant="ghost"
          size="icon"
          class="size-7"
          aria-label="ماه بعد"
          @click="shiftMonth(1)"
        >
          <Icon
            name="lucide:chevron-left"
            class="size-4"
          />
        </Button>
      </div>

      <div class="grid grid-cols-7 gap-1 text-center text-xs text-muted-foreground">
        <span
          v-for="w in JALALI_WEEKDAYS"
          :key="w"
          class="py-1"
        >{{ w }}</span>
      </div>
      <div class="grid grid-cols-7 gap-1">
        <span
          v-for="n in leadingBlanks"
          :key="`b${n}`"
        />
        <button
          v-for="d in monthLength"
          :key="d"
          type="button"
          class="grid h-8 place-items-center rounded-md text-sm transition-colors disabled:cursor-not-allowed disabled:opacity-30"
          :class="dayClass(d)"
          :disabled="isDisabled(d)"
          @click="pick(d)"
        >
          {{ toPersianDigits(d) }}
        </button>
      </div>

      <div class="mt-2 flex justify-between border-t pt-2">
        <Button
          type="button"
          variant="ghost"
          size="sm"
          class="h-7"
          :disabled="!!max && todayIso() > max"
          @click="pickToday"
        >
          امروز
        </Button>
        <Button
          type="button"
          variant="ghost"
          size="sm"
          class="h-7 text-muted-foreground"
          @click="clear"
        >
          پاک کردن
        </Button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import {
  JALALI_MONTHS, JALALI_WEEKDAYS, formatJalali, isoToJalali, jalaliMonthLength, jalaliToIso, jalaliWeekday,
  parseJalaliInput, todayIso, toPersianDigits,
} from '~/utils/jalali'

const props = defineProps<{
  modelValue: string
  max?: string // ISO, inclusive
  min?: string // ISO, inclusive
  disabled?: boolean
  invalid?: boolean
}>()
const emit = defineEmits<{ 'update:modelValue': [value: string] }>()

const root = ref<HTMLElement | null>(null)
const panel = ref(false)
const text = ref(formatJalali(props.modelValue))
const typedError = ref('')

const nowJ = isoToJalali(todayIso())!
const viewYear = ref(nowJ.jy)
const viewMonth = ref(nowJ.jm)

const selected = computed(() => isoToJalali(props.modelValue))

// Keep the text box in step when the model changes from outside (open/reset).
watch(() => props.modelValue, (v) => {
  text.value = formatJalali(v)
  typedError.value = ''
})

const years = computed(() => {
  const top = (props.max ? isoToJalali(props.max) : null)?.jy ?? nowJ.jy + 1
  const bottom = (props.min ? isoToJalali(props.min) : null)?.jy ?? top - 100
  const list: number[] = []
  for (let y = top; y >= bottom; y--) list.push(y)
  // never lose the selected / currently viewed year
  for (const y of [selected.value?.jy, viewYear.value]) if (y && !list.includes(y)) list.push(y)
  return list.sort((a, b) => b - a)
})

const monthLength = computed(() => jalaliMonthLength(viewYear.value, viewMonth.value))
const leadingBlanks = computed(() => jalaliWeekday(viewYear.value, viewMonth.value, 1))

const iso = (d: number) => jalaliToIso(viewYear.value, viewMonth.value, d)
function isDisabled(d: number) {
  const v = iso(d)
  return (!!props.max && v > props.max) || (!!props.min && v < props.min)
}
function dayClass(d: number) {
  const s = selected.value
  if (s && s.jy === viewYear.value && s.jm === viewMonth.value && s.jd === d) return 'bg-primary text-primary-foreground'
  if (iso(d) === todayIso()) return 'border border-primary/50 hover:bg-muted'
  return 'hover:bg-muted'
}

function shiftMonth(delta: number) {
  let m = viewMonth.value + delta
  let y = viewYear.value
  if (m < 1) { m = 12; y-- }
  if (m > 12) { m = 1; y++ }
  viewMonth.value = m
  viewYear.value = y
}

function togglePanel() {
  panel.value = !panel.value
  if (panel.value) {
    const j = selected.value ?? nowJ
    viewYear.value = j.jy
    viewMonth.value = j.jm
  }
}
function set(value: string) {
  typedError.value = ''
  emit('update:modelValue', value)
  text.value = formatJalali(value)
}
function pick(d: number) {
  set(iso(d))
  panel.value = false
}
function pickToday() {
  set(todayIso())
  panel.value = false
}
function clear() {
  set('')
  panel.value = false
}

// Typed input: "1404/01/01" (any digit style). Invalid text is reported and reverted.
function commitText() {
  const raw = text.value.trim()
  if (!raw) return set('')
  const parsed = parseJalaliInput(raw)
  if (!parsed) {
    typedError.value = 'تاریخ را به شکل ۱۴۰۴/۰۱/۰۱ وارد کنید.'
    return
  }
  if ((props.max && parsed > props.max) || (props.min && parsed < props.min)) {
    typedError.value = 'این تاریخ در بازه‌ی مجاز نیست.'
    return
  }
  set(parsed)
}

function onOutside(e: MouseEvent) {
  if (panel.value && root.value && !root.value.contains(e.target as Node)) panel.value = false
}
onMounted(() => document.addEventListener('mousedown', onOutside))
onBeforeUnmount(() => document.removeEventListener('mousedown', onOutside))
</script>