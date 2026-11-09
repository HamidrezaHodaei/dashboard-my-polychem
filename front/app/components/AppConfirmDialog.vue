<!-- App-wide confirmation dialog. It is the ONE host for `useConfirm().confirm(...)` and is mounted once
     in app.vue: without a mounted host the promise returned by confirm() never settles, which made every
     "delete" button (sales, payment methods, finance records...) silently do nothing. -->
<template>
  <Dialog :open="isOpen" @update:open="onOpenChange">
    <DialogContent class="sm:max-w-md" :show-close-button="false" dir="rtl">
      <DialogHeader class="text-right">
        <DialogTitle>{{ options.title }}</DialogTitle>
        <DialogDescription v-if="options.description" class="leading-7">
          {{ options.description }}
        </DialogDescription>
      </DialogHeader>
      <DialogFooter class="gap-2 sm:justify-start">
        <Button :variant="options.tone === 'danger' ? 'destructive' : 'default'" @click="resolve(true)">
          {{ options.confirmLabel || 'تأیید' }}
        </Button>
        <Button variant="outline" @click="resolve(false)">
          {{ options.cancelLabel || 'انصراف' }}
        </Button>
      </DialogFooter>
    </DialogContent>
  </Dialog>
</template>

<script setup lang="ts">
const { isOpen, options, resolve } = useConfirm()

// Closing with Esc / the overlay counts as "cancel". (After a button already resolved the promise the
// resolver is null, so this second call is a harmless no-op.)
function onOpenChange(open: boolean) {
  if (!open) resolve(false)
}
</script>
