<template>
  <WmsUiFormModal v-model="open" title="New Warehouse Transfer" subtitle="Move stock between two warehouses" submit-label="Create Transfer" :submitting="submitting" @submit="submit">
    <div class="space-y-4">
      <WmsUiSelect v-model="form.itemId" label="Item" required :options="itemOptions" placeholder="Select item" :error="errors.itemId" />

      <div class="grid grid-cols-2 gap-3">
        <WmsUiSelect v-model="form.sourceWarehouseId" label="Source Warehouse" required :options="warehouseOptions" placeholder="Select source" :error="errors.sourceWarehouseId" />
        <WmsUiSelect v-model="form.destinationWarehouseId" label="Destination Warehouse" required :options="warehouseOptions" placeholder="Select destination" :error="errors.destinationWarehouseId" />
      </div>

      <div v-if="availableAtSource !== null" class="rounded border border-line bg-paper px-3 py-2 text-xs text-ink-faint">
        Available at source: <span class="font-medium text-ink">{{ availableAtSource }}</span>
      </div>

      <div class="grid grid-cols-2 gap-3">
        <WmsUiInput v-model.number="form.quantity" type="number" label="Quantity" required :error="errors.quantity" />
        <WmsUiInput v-model="form.date" type="date" label="Date" required :error="errors.date" />
      </div>

      <WmsUiTextarea v-model="form.note" label="Note (optional)" placeholder="Reason for transfer, handling instructionsâ€¦" />
    </div>
  </WmsUiFormModal>
</template>

<script setup lang="ts">
const props = defineProps<{ modelValue: boolean }>()
const emit = defineEmits(['update:modelValue', 'created'])
const open = computed({ get: () => props.modelValue, set: (v) => emit('update:modelValue', v) })

const masterData = useMasterDataStore()
const inventoryStore = useInventoryStore()
const transferStore = useTransferStore()
const notify = useNotify()

const submitting = ref(false)
const errors = ref<Record<string, string>>({})

function emptyForm() {
  return {
    itemId: '', sourceWarehouseId: '', destinationWarehouseId: '',
    quantity: 0, date: new Date().toISOString().slice(0, 10), note: ''
  }
}
const form = ref(emptyForm())
watch(open, (v) => { if (v) { form.value = emptyForm(); errors.value = {} } })

const itemOptions = computed(() => masterData.activeItems.map((i) => ({ label: `${i.code} â€” ${i.name}`, value: i.id })))
const warehouseOptions = computed(() => masterData.activeWarehouses.map((w) => ({ label: w.name, value: w.id })))

const availableAtSource = computed(() => {
  if (!form.value.itemId || !form.value.sourceWarehouseId) return null
  const rec = inventoryStore.rows.find((r) => r.itemId === form.value.itemId && r.warehouseId === form.value.sourceWarehouseId)
  return rec?.availableQty ?? 0
})

async function submit() {
  errors.value = {}
  if (!form.value.itemId) errors.value.itemId = 'Select an item.'
  if (!form.value.sourceWarehouseId) errors.value.sourceWarehouseId = 'Select a source warehouse.'
  if (!form.value.destinationWarehouseId) errors.value.destinationWarehouseId = 'Select a destination warehouse.'
  if (form.value.sourceWarehouseId && form.value.sourceWarehouseId === form.value.destinationWarehouseId) {
    errors.value.destinationWarehouseId = 'Source and destination cannot be the same warehouse.'
  }
  if (!form.value.quantity || form.value.quantity <= 0) errors.value.quantity = 'Enter a quantity greater than zero.'
  else if (availableAtSource.value !== null && form.value.quantity > availableAtSource.value) {
    errors.value.quantity = `Transfer quantity cannot exceed available stock (${availableAtSource.value}).`
  }
  if (!form.value.date) errors.value.date = 'Date is required.'
  if (Object.keys(errors.value).length) return

  submitting.value = true
  try {
    const created = await transferStore.create({
      itemId: form.value.itemId,
      quantity: form.value.quantity,
      sourceWarehouseId: form.value.sourceWarehouseId,
      destinationWarehouseId: form.value.destinationWarehouseId,
      date: form.value.date,
      status: 'pending',
      note: form.value.note || undefined
    })
    await inventoryStore.load(true)
    notify.success('Transfer created', created.transferNumber)
    emit('created', created)
    open.value = false
  } catch (e: any) {
    errors.value.quantity = e.message
    notify.error('Transfer failed', e.message)
  } finally {
    submitting.value = false
  }
}
</script>

