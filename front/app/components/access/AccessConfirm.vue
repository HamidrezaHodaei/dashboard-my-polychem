<script setup lang="ts">
withDefaults(defineProps<{
  open: boolean
  title: string
  description?: string
  confirmLabel?: string
  tone?: 'danger' | 'default'
  loading?: boolean
}>(), { confirmLabel: 'تأیید', tone: 'default', loading: false, description: '' })

const emit = defineEmits<{
  (e: 'update:open', value: boolean): void
  (e: 'confirm'): void
}>()
</script>

<template>
  <Dialog :open="open" @update:open="emit('update:open', $event)">
    <DialogContent class="sm:max-w-md" dir="rtl">
      <DialogHeader>
        <DialogTitle>{{ title }}</DialogTitle>
        <DialogDescription>{{ description }}</DialogDescription>
      </DialogHeader>
      <slot />
      <DialogFooter>
        <Button variant="outline" :disabled="loading" @click="emit('update:open', false)">
          انصراف
        </Button>
        <Button
          :variant="tone === 'danger' ? 'destructive' : 'default'"
          :disabled="loading"
          @click="emit('confirm')"
        >
          {{ confirmLabel }}
        </Button>
      </DialogFooter>
    </DialogContent>
  </Dialog>
</template>
