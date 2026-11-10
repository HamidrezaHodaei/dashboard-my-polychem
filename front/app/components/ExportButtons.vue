<!-- <ExportButtons :disabled :busy @export="fmt => ..." /> : Excel + Word download buttons.
     The parent decides with v-if (permission) whether to render it at all. -->
<template>
  <div class="flex items-center gap-1.5">
    <Button
      variant="outline"
      size="sm"
      class="gap-2"
      :disabled="disabled || !!busy"
      title="دریافت خروجی Excel با فیلترهای فعلی"
      @click="emit('export', 'xlsx')"
    >
      <Icon
        :name="busy === 'xlsx' ? 'lucide:loader-circle' : 'lucide:file-spreadsheet'"
        class="size-4"
        :class="busy === 'xlsx' && 'animate-spin'"
      />
      Excel
    </Button>
    <Button
      variant="outline"
      size="sm"
      class="gap-2"
      :disabled="disabled || !!busy"
      title="دریافت خروجی Word با فیلترهای فعلی"
      @click="emit('export', 'docx')"
    >
      <Icon
        :name="busy === 'docx' ? 'lucide:loader-circle' : 'lucide:file-text'"
        class="size-4"
        :class="busy === 'docx' && 'animate-spin'"
      />
      Word
    </Button>
  </div>
</template>

<script setup lang="ts">
defineProps<{ disabled?: boolean, busy?: '' | 'xlsx' | 'docx' }>()
const emit = defineEmits<{ (e: 'export', format: 'xlsx' | 'docx'): void }>()
</script>
