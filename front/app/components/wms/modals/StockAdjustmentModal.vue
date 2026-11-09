<template>
  <WmsUiFormModal
    v-model="open"
    title="Stock Adjustment"
    :subtitle="row ? `${row.itemCode} آ· ${row.warehouseName}` : ''"
    submit-label="Apply Adjustment"
    :submitting="submitting"
    @submit="submit"
  >
    <div class="space-y-4">
      <div class="rounded border border-line bg-paper px-3 py-2.5 text-sm">
        <p class="font-medium text-ink">{{ row?.itemName }}</p>
        <p class="text-ink-faint">Current available: <span class="font-medium text-ink">{{ row?.availableQty }} {{ row?.unitCode }}</span></p>
      </div>

      <div class="flex gap-2">
        <button
          type="button"
          class="focus-ring flex-1 rounded border px-3 py-2 text-sm font-medium transition-colors"
          :class="direction === 'increase' ? 'border-success bg-success-soft text-success' : 'border-line text-ink-soft hover:bg-steel-50 dark:hover:bg-steel-800'"
          @click="direction = 'increase'"
        >+ Increase</button>
        <button
          type="button"
          class="focus-ring flex-1 rounded border px-3 py-2 text-sm font-medium transition-colors"
          :class="direction === 'decrease' ? 'border-danger bg-danger-soft text-danger' : 'border-line text-ink-soft hover:bg-steel-50 dark:hover:bg-steel-800'"
          @click="direction = 'decrease'"
        >âˆ’ Decrease</button>
      </div>

      <WmsUiInput v-model.number="quantity" type="number" label="Quantity" required :error="errors.quantity" />
      <WmsUiTextarea v-model="reason" label="Reason" placeholder="e.g. Cycle count correction, damaged goods, found stockâ€¦" required :error="errors.reason" />
    </div>
  </WmsUiFormModal>
</template>

<script setup lang="ts">
import type { InventoryRow } from '~/types'

const props = defineProps<{ modelValue: boolean; row: InventoryRow | null }>()
const emit = defineEmits(['update:modelValue'])

const open = computed({ get: () => props.modelValue, set: (v) => emit('update:modelValue', v) })

const inventoryStore = useInventoryStore()
const notify = useNotify()

const direction = ref<'increase' | 'decrease'>('increase')
const quantity = ref<number>(0)
const reason = ref('')
const submitting = ref(false)
const errors = ref<{ quantity?: string; reason?: string }>({})

watch(open, (v) => {
  if (v) { direction.value = 'increase'; quantity.value = 0; reason.value = ''; errors.value = {} }
})

async function submit() {
  errors.value = {}
  if (!quantity.value || quantity.value <= 0) errors.value.quantity = 'Enter a quantity greater than zero.'
  if (!reason.value.trim()) errors.value.reason = 'A reason is required for every stock adjustment.'
  if (!props.row) return
  const delta = direction.value === 'increase' ? quantity.value : -quantity.value
  if (direction.value === 'decrease' && props.row.availableQty + delta < 0) {
    errors.value.quantity = 'Cannot reduce stock below zero.'
  }
  if (Object.keys(errors.value).length) return

  submitting.value = true
  try {
    await inventoryStore.adjust({
      itemId: props.row.itemId,
      warehouseId: props.row.warehouseId,
      locationId: props.row.locationId,
      quantityDelta: delta,
      reason: reason.value,
      performedBy: 'Femke Visser'
    })
    notify.success('Stock adjusted', `${props.row.itemCode} updated by ${delta > 0 ? '+' : ''}${delta}.`)
    open.value = false
  } catch (e: any) {
    notify.error('Adjustment failed', e.message)
  } finally {
    submitting.value = false
  }
}
</script>

