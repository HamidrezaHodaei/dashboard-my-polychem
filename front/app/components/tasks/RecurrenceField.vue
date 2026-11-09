<!-- /components/tasks/RecurrenceField.vue  → <TasksRecurrenceField v-model="rule" /> -->
<!--
  وظیفه تکرارشونده: none / daily / weekly / monthly / yearly / manual span ("هر N روز / هفته / ماه / سال").
  Months and years are Jalali (done by the server). The model is null (no repeat) or
  { unit: 'DAY'|'WEEK'|'MONTH'|'YEAR', interval, end_date }.
-->
<template>
  <div class="space-y-3">
    <select
      class="field-select"
      :value="mode"
      :disabled="disabled"
      @change="pick(($event.target as HTMLSelectElement).value)"
    >
      <option value="none">
        تکرار نشود
      </option>
      <option value="DAY">
        روزانه
      </option>
      <option value="WEEK">
        هفتگی
      </option>
      <option value="MONTH">
        ماهانه (ماه شمسی)
      </option>
      <option value="YEAR">
        سالانه (سال شمسی)
      </option>
      <option value="custom">
        بازه دستی...
      </option>
    </select>

    <div
      v-if="mode === 'custom'"
      class="flex items-center gap-2 text-sm"
    >
      <span>هر</span>
      <Input
        :model-value="String(modelValue?.interval ?? 1)"
        dir="ltr"
        inputmode="numeric"
        class="h-10 w-20 text-center"
        :disabled="disabled"
        @update:model-value="v => setEvery(String(v))"
      />
      <select
        class="field-select w-28"
        :value="modelValue?.unit ?? 'DAY'"
        :disabled="disabled"
        @change="setUnit(($event.target as HTMLSelectElement).value as Unit)"
      >
        <option value="DAY">
          روز
        </option>
        <option value="WEEK">
          هفته
        </option>
        <option value="MONTH">
          ماه
        </option>
        <option value="YEAR">
          سال
        </option>
      </select>
      <span>یک‌بار</span>
    </div>

    <div
      v-if="modelValue"
      class="space-y-1.5"
    >
      <Label class="text-xs font-semibold">پایان تکرار (اختیاری)</Label>
      <JalaliDateInput
        :model-value="modelValue.end_date ?? ''"
        :disabled="disabled"
        @update:model-value="v => emitRule({ ...modelValue!, end_date: v || null })"
      />
      <p class="text-xs text-muted-foreground">
        با رسیدن موعد هر دوره، امور محوله‌ی جدیدی با همان مسئولان و چک‌لیست ساخته می‌شود.
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { RecurrenceRule } from '~/stores/taskWorkspace'

type Unit = RecurrenceRule['unit']
const props = withDefaults(defineProps<{ modelValue: RecurrenceRule | null, disabled?: boolean }>(), { disabled: false })
const emit = defineEmits<{ 'update:modelValue': [value: RecurrenceRule | null] }>()

// "custom" is a UI mode (a rule whose interval is not 1) -- remembered while the user edits it
const forceCustom = ref(false)
const mode = computed(() => {
  const r = props.modelValue
  if (!r) return forceCustom.value ? 'custom' : 'none'
  return forceCustom.value || r.interval !== 1 ? 'custom' : r.unit
})

const emitRule = (r: RecurrenceRule | null) => emit('update:modelValue', r)
function pick(value: string) {
  forceCustom.value = value === 'custom'
  if (value === 'none') return emitRule(null)
  if (value === 'custom') return emitRule({ unit: props.modelValue?.unit ?? 'DAY', interval: Math.max(props.modelValue?.interval ?? 2, 1), end_date: props.modelValue?.end_date ?? null })
  emitRule({ unit: value as Unit, interval: 1, end_date: props.modelValue?.end_date ?? null })
}
function setUnit(unit: Unit) {
  emitRule({ ...(props.modelValue ?? { interval: 1, end_date: null }), unit })
}
function setEvery(text: string) {
  const n = Number(text.replace(/[۰-۹]/g, d => String('۰۱۲۳۴۵۶۷۸۹'.indexOf(d))))
  if (!Number.isFinite(n)) return
  emitRule({ ...(props.modelValue ?? { unit: 'DAY', end_date: null }), interval: Math.min(365, Math.max(1, Math.trunc(n))) } as RecurrenceRule)
}
</script>

<style scoped>
.field-select {
  display: flex;
  height: 2.5rem;
  width: 100%;
  border: 1px solid hsl(var(--input));
  border-radius: 0.375rem;
  background: hsl(var(--background));
  padding: 0.5rem 0.75rem;
  font-size: 0.875rem;
}
</style>
