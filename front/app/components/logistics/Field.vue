<!-- /components/logistics/Field.vue  → <LogisticsField /> : label + control slot + hint/error line. -->
<template>
  <div class="space-y-1.5">
    <Label class="font-semibold">
      {{ label }}
      <span
        v-if="required"
        class="text-destructive"
      >*</span>
    </Label>
    <slot />
    <p
      v-if="error"
      class="text-xs text-destructive"
    >
      {{ error }}
    </p>
    <p
      v-else-if="hint"
      class="text-xs text-muted-foreground"
    >
      {{ hint }}
    </p>
  </div>
</template>

<script setup lang="ts">
defineProps<{ label: string, required?: boolean, error?: string, hint?: string }>()
</script>
