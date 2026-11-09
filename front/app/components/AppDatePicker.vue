<script setup lang="ts">
import { gregorianToJalali, jalaliToIso, jalaliMonthLength, jalaliMonths, todayJalali, toPersianDigits } from '~/utils/financeFormat'

const props = withDefaults(defineProps<{
  modelValue: string // ISO date string
  label?: string
  error?: string | null
  required?: boolean
}>(), {})

const emit = defineEmits<{ (e: 'update:modelValue', v: string): void }>()

const isOpen = ref(false)
const rootEl = ref<HTMLElement | null>(null)

const selected = computed<[number, number, number]>(() => {
  if (!props.modelValue) return todayJalali()
  const d = new Date(props.modelValue)
  return gregorianToJalali(d.getFullYear(), d.getMonth() + 1, d.getDate())
})

const viewYear = ref(selected.value[0])
const viewMonth = ref(selected.value[1])

const displayLabel = computed(() => {
  if (!props.modelValue) return ''
  const [y, m, d] = selected.value
  return `${toPersianDigits(d)} ${jalaliMonths[m - 1]} ${toPersianDigits(y)}`
})

const daysInMonth = computed(() => jalaliMonthLength(viewYear.value, viewMonth.value))
const leadingBlanks = computed(() => {
  // Farvardin 1 of year 1 falls on a Saturday-anchored week; approximate via
  // the Gregorian weekday of the 1st, remapped so week starts Saturday.
  const iso = jalaliToIso(viewYear.value, viewMonth.value, 1)
  const gDow = new Date(iso).getUTCDay() // 0=Sun..6=Sat
  return (gDow + 1) % 7 // shift so Saturday=0
})

function prevMonth() {
  if (viewMonth.value === 1) { viewMonth.value = 12; viewYear.value-- } else { viewMonth.value-- }
}
function nextMonth() {
  if (viewMonth.value === 12) { viewMonth.value = 1; viewYear.value++ } else { viewMonth.value++ }
}
function pick(day: number) {
  emit('update:modelValue', jalaliToIso(viewYear.value, viewMonth.value, day))
  isOpen.value = false
}

onMounted(() => {
  const handler = (e: MouseEvent) => {
    if (rootEl.value && !rootEl.value.contains(e.target as Node)) isOpen.value = false
  }
  document.addEventListener('click', handler)
  onUnmounted(() => document.removeEventListener('click', handler))
})

const weekdayHeaders = ['ش', 'ی', 'د', 'س', 'چ', 'پ', 'ج']
</script>

<template>
  <div ref="rootEl" class="relative">
    <label class="block">
      <span v-if="label" class="mb-1.5 block text-sm text-ink-800">
        {{ label }}<span v-if="required" class="text-debt-600"> *</span>
      </span>
      <button
        type="button"
        class="flex w-full items-center justify-between rounded-lg border bg-white px-3 py-2 text-sm outline-none transition-colors focus:ring-2"
        :class="error ? 'border-debt-600 focus:ring-debt-600/20' : 'border-paper-200 focus:border-gain-400 focus:ring-gain-400/20'"
        @click="isOpen = !isOpen"
      >
        <span :class="displayLabel ? 'text-ink-900' : 'text-ink-700/40'">{{ displayLabel || 'Select date' }}</span>
        <svg class="h-4 w-4 text-ink-700/50" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
          <rect x="3" y="5" width="18" height="16" rx="2" /><path d="M3 10h18M8 3v4M16 3v4" stroke-linecap="round" />
        </svg>
      </button>
      <span v-if="error" class="mt-1 block text-xs text-debt-600">{{ error }}</span>
    </label>

    <div v-if="isOpen" class="absolute z-30 mt-1 w-72 rounded-xl border border-paper-200 bg-white p-3 shadow-card">
      <div class="mb-2 flex items-center justify-between">
        <button type="button" class="rounded-lg p-1.5 hover:bg-paper-100" @click="prevMonth">
          <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 6l6 6-6 6" stroke-linecap="round" stroke-linejoin="round" /></svg>
        </button>
        <span class="text-sm font-medium text-ink-900">{{ jalaliMonths[viewMonth - 1] }} {{ toPersianDigits(viewYear) }}</span>
        <button type="button" class="rounded-lg p-1.5 hover:bg-paper-100" @click="nextMonth">
          <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M15 6l-6 6 6 6" stroke-linecap="round" stroke-linejoin="round" /></svg>
        </button>
      </div>
      <div class="grid grid-cols-7 gap-1 text-center text-xs text-ink-700/50">
        <span v-for="w in weekdayHeaders" :key="w" class="py-1">{{ w }}</span>
      </div>
      <div class="grid grid-cols-7 gap-1">
        <span v-for="n in leadingBlanks" :key="`b${n}`" />
        <button
          v-for="day in daysInMonth"
          :key="day"
          type="button"
          class="rounded-lg py-1.5 text-sm hover:bg-gain-50"
          :class="day === selected[2] && viewMonth === selected[1] && viewYear === selected[0] ? 'bg-gain-600 text-white hover:bg-gain-600' : 'text-ink-800'"
          @click="pick(day)"
        >
          {{ toPersianDigits(day) }}
        </button>
      </div>
    </div>
  </div>
</template>
