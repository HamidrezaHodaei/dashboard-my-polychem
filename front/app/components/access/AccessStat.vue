<template>
  <Card class="gap-2 p-5 shadow-none">
    <div class="flex items-center justify-between text-sm text-muted-foreground">
      <span>{{ label }}</span>
      <Icon :name="icon" class="size-4 text-primary" />
    </div>
    <p class="text-2xl font-semibold">{{ value }}</p>
  </Card>
</template>

<script setup lang="ts">
defineProps<{ label: string; value: string | number; icon: string }>()
</script>
