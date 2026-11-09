<!-- Customer picker backed by the CUSTOMER BANK (GET /api/crm/customers). The model is the bank's
     {id, name, ...}; sales are linked by that id, never by name. -->
<template>
  <div ref="root" class="relative w-full" dir="rtl">
    <div class="relative">
      <Icon name="lucide:building-2" class="pointer-events-none absolute right-3 top-2.5 size-4 text-muted-foreground" />
      <Input
        v-model="text"
        dir="rtl"
        class="w-full pr-9 text-right"
        :class="modelValue ? 'pl-9' : ''"
        :placeholder="placeholder"
        :disabled="disabled"
        :aria-invalid="invalid"
        @focus="openList"
        @input="onType"
        @keydown.esc="open = false"
      />
      <button
        v-if="modelValue && !disabled && clearable"
        type="button"
        class="absolute left-2 top-1/2 -translate-y-1/2 rounded p-1 text-muted-foreground hover:text-foreground"
        aria-label="پاک کردن مشتری"
        @click="clear"
      >
        <Icon name="lucide:x" class="size-4" />
      </button>
    </div>
    <div
      v-if="open"
      class="absolute z-50 mt-1 max-h-64 w-full overflow-y-auto rounded-lg border bg-popover p-1 text-popover-foreground shadow-md"
    >
      <p v-if="loading" class="px-3 py-2 text-xs text-muted-foreground">در حال جستجو در بانک مشتریان...</p>
      <p v-else-if="!results.length" class="px-3 py-2 text-xs text-muted-foreground">مشتری‌ای در بانک مشتریان پیدا نشد.</p>
      <button
        v-for="c in results"
        :key="c.id"
        type="button"
        class="flex w-full flex-col items-start rounded-md px-3 py-2 text-right text-sm hover:bg-accent"
        @click="choose(c)"
      >
        <span dir="auto">{{ c.name }}</span>
        <span v-if="c.province || c.industry" class="text-xs text-muted-foreground" dir="auto">
          {{ [c.province, c.industry].filter(Boolean).join(' · ') }}
        </span>
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onClickOutside, useDebounceFn } from '@vueuse/core'
import type { CrmCustomerRef } from '~/stores/crm'

const props = withDefaults(defineProps<{
  modelValue: CrmCustomerRef | null
  placeholder?: string
  disabled?: boolean
  clearable?: boolean
  invalid?: boolean
}>(), { placeholder: 'جستجوی مشتری از بانک مشتریان...', clearable: true })
const emit = defineEmits<{ 'update:modelValue': [v: CrmCustomerRef | null] }>()

const store = useCrmStore()
const root = ref<HTMLElement | null>(null)
const text = ref(props.modelValue?.name ?? '')
const open = ref(false)
const loading = ref(false)
const results = ref<CrmCustomerRef[]>([])
let seq = 0

watch(() => props.modelValue, (v) => { text.value = v?.name ?? '' })
onClickOutside(root, () => {
  open.value = false
  text.value = props.modelValue?.name ?? '' // typed-but-not-chosen text never counts as a customer
})

async function search() {
  const id = ++seq
  loading.value = true
  try {
    const rows = await store.searchCustomers(text.value.trim())
    if (id === seq) results.value = rows
  }
  catch {
    if (id === seq) results.value = []
  }
  finally {
    if (id === seq) loading.value = false
  }
}
const debounced = useDebounceFn(search, 250)
function openList() {
  open.value = true
  search()
}
function onType() {
  open.value = true
  debounced()
}
function choose(c: CrmCustomerRef) {
  emit('update:modelValue', c)
  text.value = c.name
  open.value = false
}
function clear() {
  emit('update:modelValue', null)
  text.value = ''
  results.value = []
}
</script>
