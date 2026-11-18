<!-- <PurchasesUnit v-model="unit" /> : FREE-TEXT unit. Earlier values are only suggestions (searchable);
     anything typed is accepted and is offered next time. -->
<template>
  <div class="relative">
    <Input :model-value="modelValue" placeholder="مثلاً کیلوگرم، بسته ۲۵ کیلویی…" :disabled="disabled" @update:model-value="onInput" @focus="open = true; search()" @blur="close" />
    <ul v-if="open && options.length" class="absolute z-30 mt-1 max-h-48 w-full overflow-auto rounded-md border bg-background shadow">
      <li v-for="u in options" :key="u" class="cursor-pointer px-3 py-2 text-sm hover:bg-muted" @mousedown.prevent="pick(u)">{{ u }}</li>
    </ul>
  </div>
</template>

<script setup lang="ts">
const props = defineProps<{ modelValue: string, disabled?: boolean }>()
const emit = defineEmits<{ (e: 'update:modelValue', v: string): void }>()
const store = usePurchasesStore()
const options = ref<string[]>([])
const open = ref(false)
let timer: ReturnType<typeof setTimeout> | undefined
function search() {
  clearTimeout(timer)
  timer = setTimeout(async () => {
    try { options.value = (await store.searchUnits(props.modelValue)).filter(u => u !== props.modelValue) } catch { options.value = [] }
  }, 200)
}
function onInput(v: string | number) { emit('update:modelValue', String(v)); open.value = true; search() }
function pick(u: string) { emit('update:modelValue', u); open.value = false }
function close() { setTimeout(() => { open.value = false }, 120) }
</script>
