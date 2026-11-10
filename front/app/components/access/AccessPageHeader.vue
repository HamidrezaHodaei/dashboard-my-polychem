<template>
  <div class="flex flex-col gap-4 border-b pb-6 md:flex-row md:items-end md:justify-between">
    <div>
      <div class="mb-2 flex items-center gap-2 text-xs text-muted-foreground">
        <NuxtLink to="/" class="hover:text-foreground">پیشخوان</NuxtLink>
        <Icon name="lucide:chevron-left" class="size-3" />
        <span>{{ section }}</span>
      </div>
      <h1 class="text-2xl font-semibold tracking-tight">{{ title }}</h1>
      <p class="mt-1 text-sm text-muted-foreground">{{ description }}</p>
    </div>
    <div class="flex flex-wrap items-center gap-2">
      <slot name="actions" />
      <Button v-if="actionLabel" class="gap-2" @click="$emit('action')">
        <Icon name="lucide:plus" class="size-4" />
        {{ actionLabel }}
      </Button>
    </div>
  </div>
</template>

<script setup lang="ts">
withDefaults(defineProps<{ title: string; description: string; actionLabel?: string; section?: string }>(), { section: 'مدیریت دسترسی' })
defineEmits<{ action: [] }>()
</script>
