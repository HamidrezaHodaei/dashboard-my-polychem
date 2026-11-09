<template>
  <WmsUiFormModal v-model="open" title="New Goods Issue" subtitle="Record items leaving a warehouse" size="lg" submit-label="Create Issue" :submitting="submitting" @submit="submit">
    <div class="space-y-4">
      <div class="grid grid-cols-2 gap-3">
        <WmsUiInput v-model="form.destination" label="Destination" required placeholder="e.g. Production Line 2" :error="errors.destination" />
        <WmsUiInput v-model="form.requester" label="Requester" required placeholder="Requested by" :error="errors.requester" />
      </div>
      <div class="grid grid-cols-2 gap-3">
        <WmsUiSelect v-model="form.warehouseId" label="Warehouse" required :options="warehouseOptions" placeholder="Select warehouse" :error="errors.warehouseId" />
        <WmsUiInput v-model="form.date" type="date" label="Date" required :error="errors.date" />
      </div>
      <WmsUiSelect v-model="form.status" label="Status" :options="statusOptions" />

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
        <p v-if="stockWarning" class="mt-2 text-xs text-danger">{{ stockWarning }}</p>
      </div>
    </div>
  </WmsUiFormModal>
</template>

<script setup lang="ts">
import type { GoodsIssue, IssueLine } from '~/types'

const props = defineProps<{ modelValue: boolean }>()
const emit = defineEmits(['update:modelValue', 'created'])
const open = computed({ get: () => props.modelValue, set: (v) => emit('update:modelValue', v) })

const masterData = useMasterDataStore()
const inventoryStore = useInventoryStore()
const outboundStore = useOutboundStore()
const notify = useNotify()

const submitting = ref(false)
const errors = ref<Record<string, string>>({})

function emptyForm() {
  return {
    destination: '', requester: '', warehouseId: '', date: new Date().toISOString().slice(0, 10),
    status: 'pending' as GoodsIssue['status'],
    lines: [{ id: crypto.randomUUID(), itemId: '', quantity: 0 }] as IssueLine[]
  }
}
const form = ref(emptyForm())
watch(open, (v) => { if (v) { form.value = emptyForm(); errors.value = {} } })

const warehouseOptions = computed(() => masterData.activeWarehouses.map((w) => ({ label: w.name, value: w.id })))
const itemOptions = computed(() => masterData.activeItems.map((i) => ({ label: `${i.code} â€” ${i.name}`, value: i.id })))
const statusOptions = [
  { label: 'Pending', value: 'pending' }, { label: 'Completed', value: 'completed' }
]

function addLine() { form.value.lines.push({ id: crypto.randomUUID(), itemId: '', quantity: 0 }) }
function removeLine(i: number) { if (form.value.lines.length > 1) form.value.lines.splice(i, 1) }

const stockWarning = computed(() => {
  if (!form.value.warehouseId) return ''
  for (const line of form.value.lines) {
    if (!line.itemId || !line.quantity) continue
    const rec = inventoryStore.rows.find((r) => r.itemId === line.itemId && r.warehouseId === form.value.warehouseId)
    if (!rec || rec.availableQty < line.quantity) {
      return `Not enough stock for ${rec?.itemCode ?? 'selected item'} at this warehouse (available: ${rec?.availableQty ?? 0}).`
    }
  }
  return ''
})

async function submit() {
  errors.value = {}
  if (!form.value.destination.trim()) errors.value.destination = 'Destination is required.'
  if (!form.value.requester.trim()) errors.value.requester = 'Requester is required.'
  if (!form.value.warehouseId) errors.value.warehouseId = 'Select a warehouse.'
  if (!form.value.date) errors.value.date = 'Date is required.'
  const validLines = form.value.lines.filter((l) => l.itemId && l.quantity > 0)
  if (validLines.length === 0) errors.value.lines = 'Add at least one item with a quantity greater than zero.'
  if (stockWarning.value) errors.value.lines = stockWarning.value
  if (Object.keys(errors.value).length) return

  submitting.value = true
  try {
    const created = await outboundStore.create({
      destination: form.value.destination,
      requester: form.value.requester,
      warehouseId: form.value.warehouseId,
      date: form.value.date,
      status: form.value.status,
      lines: validLines
    })
    if (created.status === 'completed') await inventoryStore.load(true)
    notify.success('Goods issue created', created.issueNumber)
    emit('created', created)
    open.value = false
  } finally {
    submitting.value = false
  }
}
</script>

