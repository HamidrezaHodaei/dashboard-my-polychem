<template>
  <WmsUiFormModal v-model="open" :title="isEdit ? 'Edit Unit' : 'New Unit'" submit-label="Save Unit" :submitting="submitting" @submit="submit">
    <div class="space-y-4">
      <WmsUiInput v-model="form.code" label="Unit Code" required monospace placeholder="e.g. PCS" :error="errors.code" />
      <WmsUiInput v-model="form.name" label="Unit Name" required placeholder="e.g. Pieces" :error="errors.name" />
    </div>
  </WmsUiFormModal>
</template>

<script setup lang="ts">
import type { Unit } from '~/types'

const props = defineProps<{ modelValue: boolean; unit: Unit | null }>()
const emit = defineEmits(['update:modelValue', 'saved'])
const open = computed({ get: () => props.modelValue, set: (v) => emit('update:modelValue', v) })
const isEdit = computed(() => !!props.unit)

const notify = useNotify()
const submitting = ref(false)
const errors = ref<Record<string, string>>({})

const form = ref({ id: '', code: '', name: '' })
watch(open, (v) => {
  if (v) {
    errors.value = {}
    form.value = props.unit ? { ...props.unit } : { id: '', code: '', name: '' }
  }
})

async function submit() {
  errors.value = {}
  if (!form.value.code.trim()) errors.value.code = 'Unit code is required.'
  if (!form.value.name.trim()) errors.value.name = 'Unit name is required.'
  if (Object.keys(errors.value).length) return
  submitting.value = true
  await new Promise((r) => setTimeout(r, 150))
  emit('saved', { ...form.value, id: form.value.id || `unit-${Date.now()}` })
  notify.success(isEdit.value ? 'Unit updated' : 'Unit created', form.value.name)
  submitting.value = false
  open.value = false
}
</script>

