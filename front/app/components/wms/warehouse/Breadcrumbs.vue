<template>
  <nav class="flex items-center gap-1.5 text-sm">
    <template v-for="(crumb, i) in crumbs" :key="i">
      <NuxtLink v-if="crumb.to && i < crumbs.length - 1" :to="crumb.to" class="text-ink-faint hover:text-ink">{{ crumb.label }}</NuxtLink>
      <span v-else class="font-medium text-ink">{{ crumb.label }}</span>
      <span v-if="i < crumbs.length - 1" class="text-ink-faint">/</span>
    </template>
  </nav>
</template>

<script setup lang="ts">
defineProps<{ crumbs: { label: string; to?: string }[] }>()
</script>

