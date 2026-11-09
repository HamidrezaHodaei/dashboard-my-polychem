<!-- /components/logistics/Checklist.vue  → <LogisticsChecklist /> -->
<!-- Multi-select as a scrollable grid of checkboxes (cargo types, countries, cities). -->
<template>
  <div
    class="grid max-h-52 gap-1 overflow-y-auto rounded-lg border p-2 sm:grid-cols-3"
    :class="invalid ? 'border-destructive' : 'border-input'"
  >
    <label
      v-for="o in options"
      :key="o.code"
      class="flex cursor-pointer items-center gap-2 rounded-md px-2 py-1.5 text-sm hover:bg-muted/50"
    >
      <Checkbox
        :model-value="modelValue.includes(o.code)"
        @update:model-value="toggle(o.code)"
      />
      <span class="min-w-0 truncate">{{ o.label }}</span>
    </label>
    <p
      v-if="!options.length"
      class="col-span-full p-2 text-center text-xs text-muted-foreground"
    >
      {{ emptyText }}
    </p>
  </div>
</template>

<script setup lang="ts">
import type { Option } from '~/utils/logistics-form'

const props = withDefaults(defineProps<{
  options: Option[]
  modelValue: string[]
  invalid?: boolean
  emptyText?: string
}>(), { invalid: false, emptyText: 'موردی برای انتخاب وجود ندارد.' })

const emit = defineEmits<{ 'update:modelValue': [value: string[]] }>()

function toggle(code: string) {
  const next = props.modelValue.includes(code)
    ? props.modelValue.filter(c => c !== code)
    : [...props.modelValue, code]
  emit('update:modelValue', next)
}
</script>
