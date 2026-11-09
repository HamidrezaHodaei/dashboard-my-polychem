<template>
  <WmsUiFormModal v-model="open" :title="isEdit ? 'Edit Storage Location' : 'New Storage Location'" submit-label="Save Location" :submitting="submitting" @submit="submit">
    <div class="space-y-4">
      <WmsUiInput v-model="form.code" label="Location Code" required monospace placeholder="e.g. A-01-01" :error="errors.code" />
      <WmsUiInput v-model="form.name" label="Description" required placeholder="e.g. Aisle A, Rack 1, Bin 1" :error="errors.name" />
      <WmsUiSelect v-model="form.warehouseId" label="Warehouse" required :options="warehouseOptions" placeholder="Select warehouse" :error="errors.warehouseId" />
      <WmsUiSelect v-model="form.status" label="Status" :options="statusOptions" />
    </div>
  </WmsUiFormModal>
</template>

<script setup lang="ts">
import type { StorageLocation } from '~/types'

const props = defineProps<{ modelValue: boolean; location: StorageLocation | null }>()
const emit = defineEmits(['update:modelValue', 'saved'])
const open = computed({ get: () => props.modelValue, set: (v) => emit('update:modelValue', v) })
const isEdit = computed(() => !!props.location)

const masterData = useMasterDataStore()
const notify = useNotify()
const submitting = ref(false)
const errors = ref<Record<string, string>>({})
const statusOptions = [{ label: 'Active', value: 'active' }, { label: 'Inactive', value: 'inactive' }]
const warehouseOptions = computed(() => masterData.warehouses.map((w) => ({ label: w.name, value: w.id })))

const form = ref({ id: '', code: '', name: '', warehouseId: '', status: 'active' as 'active' | 'inactive' })
watch(open, (v) => {
  if (v) {
    errors.value = {}
    form.value = props.location ? { ...props.location } : { id: '', code: '', name: '', warehouseId: '', status: 'active' }
  }
})

async function submit() {
  errors.value = {}
  if (!form.value.code.trim()) errors.value.code = 'Location code is required.'
  if (!form.value.name.trim()) errors.value.name = 'Description is required.'
  if (!form.value.warehouseId) errors.value.warehouseId = 'Select a warehouse.'
  if (Object.keys(errors.value).length) return
  submitting.value = true
  await new Promise((r) => setTimeout(r, 150))
  emit('saved', { ...form.value, id: form.value.id || `loc-${Date.now()}` })
  notify.success(isEdit.value ? 'Location updated' : 'Location created', form.value.code)
  submitting.value = false
  open.value = false
}
</script>

