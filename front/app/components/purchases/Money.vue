<!-- <PurchasesMoney v-model="n" rial /> : number input shown with thousands separators (1,500,000,000); empty = null.
     With `rial` the field is a whole-rial price: «ریال» is shown inside the box and no decimals are accepted.
     Only the display is formatted — the model is the plain number. -->
<template>
  <div class="relative">
    <Input
      :model-value="display"
      dir="ltr"
      inputmode="decimal"
      class="text-right"
      :class="rial && 'pl-14'"
      :placeholder="placeholder"
      :disabled="disabled"
      :aria-invalid="invalid"
      @update:model-value="onInput"
    />
    <span v-if="rial" class="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-xs text-muted-foreground">ریال</span>
  </div>
</template>

<script setup lang="ts">
const props = defineProps<{ modelValue: number | null | undefined, placeholder?: string, disabled?: boolean, invalid?: boolean, decimals?: number, rial?: boolean }>()
const emit = defineEmits<{ (e: 'update:modelValue', v: number | null): void }>()
const raw = ref<string | null>(null) // what is being typed (so "12." is not eaten)
const maxDecimals = computed(() => (props.rial ? 0 : props.decimals ?? 2))

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
  const decPart = dec === undefined || maxDecimals.value === 0 ? undefined : dec.slice(0, maxDecimals.value)
  const intFmt = int.replace(/\B(?=(\d{3})+(?!\d))/g, ',')
  raw.value = decPart === undefined ? intFmt : `${intFmt}.${decPart}`
  const numeric = decPart === undefined ? int : `${int}.${decPart}`
  emit('update:modelValue', numeric === '' || numeric === '.' ? null : Number(numeric))
}
</script>
