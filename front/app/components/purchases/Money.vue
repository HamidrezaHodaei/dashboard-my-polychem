<!-- <PurchasesMoney v-model="n" /> : number input shown with thousands separators; empty = null. -->
<template>
  <Input
    :model-value="display"
    dir="ltr"
    inputmode="decimal"
    class="text-right"
    :placeholder="placeholder"
    :disabled="disabled"
    :aria-invalid="invalid"
    @update:model-value="onInput"
  />
</template>

<script setup lang="ts">
const props = defineProps<{ modelValue: number | null | undefined, placeholder?: string, disabled?: boolean, invalid?: boolean, decimals?: number }>()
const emit = defineEmits<{ (e: 'update:modelValue', v: number | null): void }>()
const raw = ref<string | null>(null) // what is being typed (so "12." is not eaten)

const display = computed(() => {
  if (raw.value !== null) return raw.value
  if (props.modelValue === null || props.modelValue === undefined) return ''
  return Number(props.modelValue).toLocaleString('en-US', { maximumFractionDigits: 3 })
})
watch(() => props.modelValue, (v) => {
  // keep what is being typed ("12." must not collapse to "12") unless the value was changed from outside
  if (raw.value === null) return
  const t = raw.value.replace(/,/g, '')
  const typed = t === '' || t === '.' ? null : Number(t)
  if (typed !== (v ?? null)) raw.value = null
})

function onInput(v: string | number) {
  // Persian / Arabic digits are accepted too
  const text = String(v).replace(/[۰-۹]/g, d => String('۰۱۲۳۴۵۶۷۸۹'.indexOf(d))).replace(/[٠-٩]/g, d => String('٠١٢٣٤٥٦٧٨٩'.indexOf(d)))
    .replace(/[^\d.]/g, '')
  const [int = '', dec] = text.split('.')
  const decPart = dec === undefined ? undefined : dec.slice(0, props.decimals ?? 2)
  const intFmt = int.replace(/\B(?=(\d{3})+(?!\d))/g, ',')
  raw.value = decPart === undefined ? intFmt : `${intFmt}.${decPart}`
  const numeric = decPart === undefined ? int : `${int}.${decPart}`
  emit('update:modelValue', numeric === '' || numeric === '.' ? null : Number(numeric))
}
</script>
