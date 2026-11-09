<template>
  <div class="rounded-md border border-line bg-paper-raised" :class="padded ? 'p-5' : ''">
    <div v-if="title || $slots.actions" class="mb-4 flex items-center justify-between gap-3" :class="padded ? '' : 'p-5 pb-0'">
      <div>
        <h3 v-if="title" class="text-sm font-semibold text-ink">{{ title }}</h3>
        <p v-if="subtitle" class="mt-0.5 text-xs text-ink-faint">{{ subtitle }}</p>
      </div>
      <div class="flex items-center gap-2">
        <slot name="actions" />
      </div>
    </div>
    <div :class="padded ? '' : 'px-5 pb-5'">
      <slot />
    </div>
  </div>
</template>

<script setup lang="ts">
withDefaults(defineProps<{ title?: string; subtitle?: string; padded?: boolean }>(), { padded: true })
</script>

