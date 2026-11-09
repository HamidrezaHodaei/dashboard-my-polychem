<template>
  <WmsUiFormModal v-model="open" :title="isEdit ? 'Edit Category' : 'New Category'" submit-label="Save Category" :submitting="submitting" @submit="submit">
    <div class="space-y-4">
      <WmsUiInput v-model="form.name" label="Category Name" required :error="errors.name" />
      <WmsUiSelect v-model="form.status" label="Status" :options="statusOptions" />
    </div>
  </WmsUiFormModal>
</template>

<script setup lang="ts">
import type { ItemCategory } from '~/types'

const props = defineProps<{ modelValue: boolean; category: ItemCategory | null }>()
const emit = defineEmits(['update:modelValue', 'saved'])
const open = computed({ get: () => props.modelValue, set: (v) => emit('update:modelValue', v) })
const isEdit = computed(() => !!props.category)

const notify = useNotify()
const submitting = ref(false)
const errors = ref<Record<string, string>>({})
const statusOptions = [{ label: 'Active', value: 'active' }, { label: 'Inactive', value: 'inactive' }]

const form = ref({ id: '', name: '', status: 'active' as 'active' | 'inactive' })
watch(open, (v) => {
  if (v) {
    errors.value = {}
    form.value = props.category ? { ...props.category } : { id: '', name: '', status: 'active' }
  }
})

async function submit() {
  errors.value = {}
  if (!form.value.name.trim()) errors.value.name = 'Category name is required.'
  if (Object.keys(errors.value).length) return
  submitting.value = true
  await new Promise((r) => setTimeout(r, 150))
  emit('saved', { ...form.value, id: form.value.id || `cat-${Date.now()}` })
  notify.success(isEdit.value ? 'Category updated' : 'Category created', form.value.name)
  submitting.value = false
  open.value = false
}
</script>

