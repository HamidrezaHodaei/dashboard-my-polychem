<!--/components/mail/RecipientPicker.vue → <MailRecipientPicker /> : search & pick any number of users (chips) -->
<script setup lang="ts">
import type { MailPerson } from '~/utils/mail'

const props = defineProps<{ modelValue: MailPerson[], placeholder?: string, exclude?: number[] }>()
const emit = defineEmits<{ 'update:modelValue': [MailPerson[]] }>()

const store = useMailStore()
const query = ref('')
const results = ref<MailPerson[]>([])
const open = ref(false)
const busy = ref(false)
const active = ref(0)
let timer: ReturnType<typeof setTimeout> | undefined
let seq = 0

const takenIds = computed(() => [...props.modelValue.map(p => p.id), ...(props.exclude || [])])

async function run() {
  const mine = ++seq
  busy.value = true
  try {
    const found = await store.searchPeople(query.value, takenIds.value)
    if (mine === seq) { results.value = found; active.value = 0 }
  }
  catch { if (mine === seq) results.value = [] }
  finally { if (mine === seq) busy.value = false }
}
watch(query, () => {
  clearTimeout(timer)
  timer = setTimeout(run, 250)
})
function onFocus() { open.value = true; run() }
function onBlur() { setTimeout(() => (open.value = false), 150) }
function add(p: MailPerson) {
  emit('update:modelValue', [...props.modelValue, p])
  query.value = ''
  results.value = results.value.filter(r => r.id !== p.id)
}
function remove(id: number) { emit('update:modelValue', props.modelValue.filter(p => p.id !== id)) }
function onKey(e: KeyboardEvent) {
  if (e.key === 'ArrowDown') { active.value = Math.min(active.value + 1, results.value.length - 1); e.preventDefault() }
  else if (e.key === 'ArrowUp') { active.value = Math.max(active.value - 1, 0); e.preventDefault() }
  else if (e.key === 'Enter' && results.value[active.value]) { add(results.value[active.value]!); e.preventDefault() }
  else if (e.key === 'Backspace' && !query.value && props.modelValue.length) remove(props.modelValue.at(-1)!.id)
}
</script>

<template>
  <div class="relative" dir="rtl">
    <div class="flex min-h-11 flex-wrap items-center gap-1.5 rounded-md border bg-background px-2 py-1 focus-within:ring-2 focus-within:ring-ring/40 sm:min-h-9">
      <span
        v-for="p in modelValue"
        :key="p.id"
        class="flex max-w-full items-center gap-1 rounded-sm border bg-muted/50 py-0.5 ps-2 pe-0.5 text-xs"
      >
        <span class="max-w-40 truncate sm:max-w-56">{{ p.full_name }}</span>
        <button type="button" class="px-2 py-1.5 text-base leading-none text-muted-foreground hover:text-destructive" :aria-label="`حذف ${p.full_name}`" @click="remove(p.id)">
          ×
        </button>
      </span>
      <input
        v-model="query"
        dir="auto"
        class="min-w-32 flex-1 bg-transparent py-2 text-right text-sm outline-none sm:py-1 placeholder:text-right placeholder:text-muted-foreground"
        :placeholder="modelValue.length ? '' : (placeholder || 'جست‌وجوی نام، نام کاربری یا ایمیل')"
        @focus="onFocus"
        @blur="onBlur"
        @keydown="onKey"
      >
    </div>

    <div
      v-if="open"
      class="absolute inset-x-0 top-full z-50 mt-1 max-h-64 overflow-y-auto rounded-md border bg-popover p-1 shadow-md"
    >
      <p v-if="busy && !results.length" class="p-3 text-center text-xs text-muted-foreground">
        در حال جست‌وجو…
      </p>
      <p v-else-if="!results.length" class="p-3 text-center text-xs text-muted-foreground">
        کاربری با این مشخصات یافت نشد.
      </p>
      <button
        v-for="(p, i) in results"
        :key="p.id"
        type="button"
        class="flex min-h-11 w-full items-center gap-2 rounded-sm px-2 py-1.5 text-start hover:bg-accent"
        :class="i === active && 'bg-accent'"
        @mousedown.prevent="add(p)"
      >
        <span class="min-w-0 flex-1">
          <span class="block truncate text-sm">{{ p.full_name }}</span>
          <span class="block truncate text-xs text-muted-foreground" dir="ltr">{{ p.email }} · @{{ p.username }}</span>
        </span>
        <span v-if="p.department" class="shrink-0 text-[11px] text-muted-foreground">{{ p.department }}</span>
      </button>
    </div>
  </div>
</template>
