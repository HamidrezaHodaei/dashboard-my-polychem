<template>
  <WmsUiFormModal v-model="open" :title="isEdit ? 'Edit Warehouse' : 'New Warehouse'" submit-label="Save Warehouse" :submitting="submitting" @submit="submit">
    <div class="space-y-4">
      <WmsUiInput v-model="form.code" label="Warehouse Code" required monospace placeholder="e.g. WH-AMS" :error="errors.code" />
      <WmsUiInput v-model="form.name" label="Warehouse Name" required :error="errors.name" />
      <WmsUiTextarea v-model="form.address" label="Address" required :error="errors.address" />
      <WmsUiSelect v-model="form.status" label="Status" :options="statusOptions" />
    </div>
  </WmsUiFormModal>
</template>

<script setup lang="ts">
import type { Warehouse } from '~/types'

const props = defineProps<{ modelValue: boolean; warehouse: Warehouse | null }>()
const emit = defineEmits(['update:modelValue'])
const open = computed({ get: () => props.modelValue, set: (v) => emit('update:modelValue', v) })
const isEdit = computed(() => !!props.warehouse)

const masterData = useMasterDataStore()
const notify = useNotify()
const submitting = ref(false)
const errors = ref<Record<string, string>>({})
const statusOptions = [{ label: 'Active', value: 'active' }, { label: 'Inactive', value: 'inactive' }]

const form = ref({ id: '', code: '', name: '', address: '', status: 'active' as 'active' | 'inactive' })
watch(open, (v) => {
  if (v) {
    errors.value = {}
    form.value = props.warehouse ? { ...props.warehouse } : { id: '', code: '', name: '', address: '', status: 'active' }
  }
})

async function submit() {
  errors.value = {}
  if (!form.value.code.trim()) errors.value.code = 'Warehouse code is required.'
  if (!form.value.name.trim()) errors.value.name = 'Warehouse name is required.'
  if (!form.value.address.trim()) errors.value.address = 'Address is required.'
  if (Object.keys(errors.value).length) return

  submitting.value = true
  try {
    await masterData.saveWarehouse({ ...form.value } as Warehouse)
    notify.success(isEdit.value ? 'Warehouse updated' : 'Warehouse created', form.value.name)
    open.value = false
  } finally {
    submitting.value = false
  }
}
</script>

