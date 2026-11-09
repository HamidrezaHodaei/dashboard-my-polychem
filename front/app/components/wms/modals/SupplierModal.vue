<template>
  <WmsUiFormModal v-model="open" :title="isEdit ? 'Edit Supplier' : 'New Supplier'" submit-label="Save Supplier" :submitting="submitting" @submit="submit">
    <div class="space-y-4">
      <WmsUiInput v-model="form.code" label="Supplier Code" required monospace placeholder="e.g. SUP-005" :error="errors.code" />
      <WmsUiInput v-model="form.name" label="Company Name" required :error="errors.name" />
      <div class="grid grid-cols-2 gap-3">
        <WmsUiInput v-model="form.contact" label="Contact Person" required :error="errors.contact" />
        <WmsUiInput v-model="form.email" type="email" label="Email" required :error="errors.email" />
      </div>
      <WmsUiSelect v-model="form.status" label="Status" :options="statusOptions" />
    </div>
  </WmsUiFormModal>
</template>

<script setup lang="ts">
import type { Supplier } from '~/types'

const props = defineProps<{ modelValue: boolean; supplier: Supplier | null }>()
const emit = defineEmits(['update:modelValue'])
const open = computed({ get: () => props.modelValue, set: (v) => emit('update:modelValue', v) })
const isEdit = computed(() => !!props.supplier)

const masterData = useMasterDataStore()
const notify = useNotify()
const submitting = ref(false)
const errors = ref<Record<string, string>>({})
const statusOptions = [{ label: 'Active', value: 'active' }, { label: 'Inactive', value: 'inactive' }]

const form = ref({ id: '', code: '', name: '', contact: '', email: '', status: 'active' as 'active' | 'inactive' })
watch(open, (v) => {
  if (v) {
    errors.value = {}
    form.value = props.supplier ? { ...props.supplier } : { id: '', code: '', name: '', contact: '', email: '', status: 'active' }
  }
})

async function submit() {
  errors.value = {}
  if (!form.value.code.trim()) errors.value.code = 'Supplier code is required.'
  if (!form.value.name.trim()) errors.value.name = 'Company name is required.'
  if (!form.value.contact.trim()) errors.value.contact = 'Contact person is required.'
  if (!form.value.email.trim() || !form.value.email.includes('@')) errors.value.email = 'Enter a valid email address.'
  if (Object.keys(errors.value).length) return

  submitting.value = true
  try {
    await masterData.saveSupplier({ ...form.value } as Supplier)
    notify.success(isEdit.value ? 'Supplier updated' : 'Supplier created', form.value.name)
    open.value = false
  } finally {
    submitting.value = false
  }
}
</script>

