<template>
  <WmsUiFormModal v-model="open" title="New Goods Receipt" subtitle="Record items arriving into a warehouse" size="lg" submit-label="Create Receipt" :submitting="submitting" @submit="submit">
    <div class="space-y-4">
      <div class="grid grid-cols-2 gap-3">
        <WmsUiSelect v-model="form.supplierId" label="Supplier" required :options="supplierOptions" placeholder="Select supplier" :error="errors.supplierId" />
        <WmsUiSelect v-model="form.warehouseId" label="Warehouse" required :options="warehouseOptions" placeholder="Select warehouse" :error="errors.warehouseId" />
      </div>
      <div class="grid grid-cols-2 gap-3">
        <WmsUiInput v-model="form.date" type="date" label="Date" required :error="errors.date" />
        <WmsUiSelect v-model="form.status" label="Status" :options="statusOptions" />
      </div>

      <div>
        <div class="mb-1.5 flex items-center justify-between">
          <span class="text-sm font-medium text-ink">Items</span>
          <WmsUiButton size="sm" variant="ghost" @click="addLine">
            <template #icon><svg class="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" d="M12 5v14m-7-7h14" /></svg></template>
            Add line
          </WmsUiButton>
        </div>
        <div v-if="errors.lines" class="mb-2 text-xs text-danger">{{ errors.lines }}</div>
        <div class="space-y-2">
          <div v-for="(line, i) in form.lines" :key="line.id" class="flex items-end gap-2">
            <WmsUiSelect v-model="line.itemId" :options="itemOptions" placeholder="Select item" class="flex-1" />
            <WmsUiInput v-model.number="line.quantity" type="number" placeholder="Qty" class="w-28" />
            <button class="focus-ring mb-1 rounded p-1.5 text-ink-faint hover:bg-danger-soft hover:text-danger" @click="removeLine(i)">
              <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" d="M6 18L18 6M6 6l12 12" /></svg>
            </button>
          </div>
        </div>
      </div>
    </div>
  </WmsUiFormModal>
</template>

<script setup lang="ts">
import type { GoodsReceipt, ReceiptLine } from '~/types'

const props = defineProps<{ modelValue: boolean }>()
const emit = defineEmits(['update:modelValue', 'created'])
const open = computed({ get: () => props.modelValue, set: (v) => emit('update:modelValue', v) })

const masterData = useMasterDataStore()
const inboundStore = useInboundStore()
const notify = useNotify()

const submitting = ref(false)
const errors = ref<Record<string, string>>({})

function emptyForm() {
  return {
    supplierId: '', warehouseId: '', date: new Date().toISOString().slice(0, 10),
    status: 'pending' as GoodsReceipt['status'],
    lines: [{ id: crypto.randomUUID(), itemId: '', quantity: 0 }] as ReceiptLine[]
  }
}
const form = ref(emptyForm())

watch(open, (v) => { if (v) { form.value = emptyForm(); errors.value = {} } })

const supplierOptions = computed(() => masterData.suppliers.filter((s) => s.status === 'active').map((s) => ({ label: s.name, value: s.id })))
const warehouseOptions = computed(() => masterData.activeWarehouses.map((w) => ({ label: w.name, value: w.id })))
const itemOptions = computed(() => masterData.activeItems.map((i) => ({ label: `${i.code} â€” ${i.name}`, value: i.id })))
const statusOptions = [
  { label: 'Draft', value: 'draft' }, { label: 'Pending', value: 'pending' }, { label: 'Completed', value: 'completed' }
]

function addLine() { form.value.lines.push({ id: crypto.randomUUID(), itemId: '', quantity: 0 }) }
function removeLine(i: number) { if (form.value.lines.length > 1) form.value.lines.splice(i, 1) }

async function submit() {
  errors.value = {}
  if (!form.value.supplierId) errors.value.supplierId = 'Select a supplier.'
  if (!form.value.warehouseId) errors.value.warehouseId = 'Select a warehouse.'
  if (!form.value.date) errors.value.date = 'Date is required.'
  const validLines = form.value.lines.filter((l) => l.itemId && l.quantity > 0)
  if (validLines.length === 0) errors.value.lines = 'Add at least one item with a quantity greater than zero.'
  if (Object.keys(errors.value).length) return

  submitting.value = true
  try {
    const created = await inboundStore.create({
      supplierId: form.value.supplierId,
      warehouseId: form.value.warehouseId,
      date: form.value.date,
      status: form.value.status,
      lines: validLines,
      createdBy: 'Femke Visser'
    })
    notify.success('Goods receipt created', created.receiptNumber)
    emit('created', created)
    open.value = false
  } finally {
    submitting.value = false
  }
}
</script>

