<template>
  <WmsUiFormModal v-model="open" :title="isEdit ? 'Edit Employee' : 'New Employee'" submit-label="Save Employee" :submitting="submitting" @submit="submit">
    <div class="space-y-4">
      <WmsUiInput v-model="form.name" label="Full Name" required :error="errors.name" />
      <WmsUiInput v-model="form.email" type="email" label="Email" required :error="errors.email" />
      <div class="grid grid-cols-2 gap-3">
        <WmsUiSelect v-model="form.role" label="Role" required :options="roleOptions" />
        <WmsUiSelect v-model="form.status" label="Status" :options="statusOptions" />
      </div>
    </div>
  </WmsUiFormModal>
</template>

<script setup lang="ts">
import type { Employee } from '~/types'

const props = defineProps<{ modelValue: boolean; employee: Employee | null }>()
const emit = defineEmits(['update:modelValue'])
const open = computed({ get: () => props.modelValue, set: (v) => emit('update:modelValue', v) })
const isEdit = computed(() => !!props.employee)

const masterData = useMasterDataStore()
const notify = useNotify()
const submitting = ref(false)
const errors = ref<Record<string, string>>({})

const roleOptions = [
  { label: 'Administrator', value: 'admin' },
  { label: 'Warehouse Manager', value: 'warehouse_manager' },
  { label: 'Operator', value: 'operator' },
  { label: 'Viewer', value: 'viewer' }
]
const statusOptions = [{ label: 'Active', value: 'active' }, { label: 'Inactive', value: 'inactive' }]

const form = ref({ id: '', name: '', email: '', role: 'operator' as Employee['role'], status: 'active' as 'active' | 'inactive' })
watch(open, (v) => {
  if (v) {
    errors.value = {}
    form.value = props.employee ? { ...props.employee } : { id: '', name: '', email: '', role: 'operator', status: 'active' }
  }
})

async function submit() {
  errors.value = {}
  if (!form.value.name.trim()) errors.value.name = 'Name is required.'
  if (!form.value.email.trim() || !form.value.email.includes('@')) errors.value.email = 'Enter a valid email address.'
  if (Object.keys(errors.value).length) return

  submitting.value = true
  try {
    await masterData.saveEmployee({ ...form.value } as Employee)
    notify.success(isEdit.value ? 'Employee updated' : 'Employee created', form.value.name)
    open.value = false
  } finally {
    submitting.value = false
  }
}
</script>

