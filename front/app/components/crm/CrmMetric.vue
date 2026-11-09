<template>
  <Card
    class="gap-3 p-5 shadow-none transition-transform hover:-translate-y-0.5"
    :class="tone === 'primary' && 'border-primary/30 bg-primary/5'"
  >
    <div class="flex items-center justify-between">
      <span class="text-sm text-muted-foreground">{{ label }}</span><div class="flex size-9 items-center justify-center rounded-lg bg-primary/10 text-primary">
        <Icon
          :name="icon"
          class="size-4"
        />
      </div>
    </div><p class="truncate text-xl font-semibold">
      {{ value }}
    </p>
  </Card>
</template>

<script setup lang="ts">
defineProps<{ label: string, value: string | number, icon: string, tone?: 'primary' | 'default' }>()
</script>
