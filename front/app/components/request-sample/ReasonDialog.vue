<!-- A small dialog that asks for a note / reason (reject, hold, cancel, approve, complete, convert...). -->
<template>
  <Dialog :open="open" @update:open="v => emit('update:open', v)">
    <DialogContent dir="rtl" class="rs-rtl sm:max-w-md">
      <DialogHeader class="text-right">
        <DialogTitle>{{ title }}</DialogTitle>
        <DialogDescription v-if="description">{{ description }}</DialogDescription>
      </DialogHeader>
      <div class="space-y-1.5">
        <Label>{{ label }} <span v-if="required" class="text-destructive">*</span></Label>
        <Textarea v-model="note" rows="3" dir="rtl" :aria-invalid="!!error" />
        <p v-if="error" class="text-xs text-destructive">{{ error }}</p>
      </div>
      <DialogFooter class="gap-2 sm:justify-start">
        <Button :variant="tone === 'danger' ? 'destructive' : 'default'" :disabled="saving" @click="submit">
          {{ confirmLabel }}
        </Button>
        <Button variant="outline" :disabled="saving" @click="emit('update:open', false)">انصراف</Button>
      </DialogFooter>
    </DialogContent>
  </Dialog>
</template>

<script setup lang="ts">
const props = withDefaults(defineProps<{
  open: boolean, title: string, description?: string, label?: string, required?: boolean,
  confirmLabel?: string, tone?: 'danger' | 'default', saving?: boolean
}>(), { label: 'توضیحات', confirmLabel: 'تأیید', tone: 'default' })
const emit = defineEmits<{ (e: 'update:open', v: boolean): void, (e: 'confirm', note: string): void }>()
const note = ref('')
const error = ref('')
watch(() => props.open, (v) => { if (v) { note.value = ''; error.value = '' } })
function submit() {
  if (props.required && !note.value.trim()) { error.value = 'این فیلد الزامی است.'; return }
  emit('confirm', note.value.trim())
}
</script>
