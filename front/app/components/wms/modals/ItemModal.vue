<template>
  <WmsUiFormModal
    v-model="open"
    :title="isEdit ? 'Edit Item' : 'New Item'"
    submit-label="Save Item"
    :submitting="submitting"
    @submit="submit"
  >
    <div class="space-y-4">
      <WmsUiInput v-model="form.code" label="Item Code" required monospace placeholder="e.g. ELE-1003" :error="errors.code" />
      <WmsUiInput v-model="form.name" label="Item Name" required :error="errors.name" />
      <div class="grid grid-cols-2 gap-3">
        <WmsUiSelect v-model="form.categoryId" label="Category" required :options="categoryOptions" :error="errors.categoryId" />
        <WmsUiSelect v-model="form.unitId" label="Unit" required :options="unitOptions" :error="errors.unitId" />
      </div>
      <WmsUiSelect v-model="form.status" label="Status" :options="statusOptions" />
    </div>
  </WmsUiFormModal>
</template>

<script setup lang="ts">
import type { Item } from '~/types'

const props = defineProps<{ modelValue: boolean; item: Item | null }>()
const emit = defineEmits(['update:modelValue'])

const open = computed({ get: () => props.modelValue, set: (v) => emit('update:modelValue', v) })
const isEdit = computed(() => !!props.item)

const masterData = useMasterDataStore()
const notify = useNotify()
const submitting = ref(false)
const errors = ref<Record<string, string>>({})

const form = ref({ id: '', code: '', name: '', categoryId: '', unitId: '', status: 'active' as 'active' | 'inactive' })

watch(open, (v) => {
  if (v) {
    errors.value = {}
    form.value = props.item
      ? { ...props.item }
      : { id: '', code: '', name: '', categoryId: '', unitId: '', status: 'active' }
  }
})

const categoryOptions = computed(() => masterData.categories.map((c) => ({ label: c.name, value: c.id })))
const unitOptions = computed(() => masterData.units.map((u) => ({ label: `${u.name} (${u.code})`, value: u.id })))
const statusOptions = [{ label: 'Active', value: 'active' }, { label: 'Inactive', value: 'inactive' }]

async function submit() {
  errors.value = {}
  if (!form.value.code.trim()) errors.value.code = 'Item code is required.'
  if (!form.value.name.trim()) errors.value.name = 'Item name is required.'
  if (!form.value.categoryId) errors.value.categoryId = 'Select a category.'
  if (!form.value.unitId) errors.value.unitId = 'Select a unit.'
  if (Object.keys(errors.value).length) return

  submitting.value = true
  try {
    await masterData.saveItem({ ...form.value } as Item)
    notify.success(isEdit.value ? 'Item updated' : 'Item created', form.value.name)
    open.value = false
  } finally {
    submitting.value = false
  }
}
</script>

