<template>
  <WmsUiBaseModal :model-value="isOpen" :title="options.title" size="sm" @update:model-value="(v) => !v && resolve(false)">
    <p class="text-sm text-ink-soft">{{ options.description }}</p>
    <template #footer>
      <WmsUiButton variant="ghost" @click="resolve(false)">Cancel</WmsUiButton>
      <WmsUiButton :variant="options.tone === 'danger' ? 'danger' : 'primary'" @click="resolve(true)">
        {{ options.confirmLabel || 'Confirm' }}
      </WmsUiButton>
    </template>
  </WmsUiBaseModal>
</template>

<script setup lang="ts">
const { isOpen, options, resolve } = useConfirm()
</script>

