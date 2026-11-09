<!-- /components/tasks/AssigneePicker.vue  → <TasksAssigneePicker /> -->
<!-- Choose any number of people for a task (searchable checklist). -->
<template>
  <div class="space-y-2">
    <Input
      v-if="users.length > 6"
      v-model="term"
      dir="rtl"
      placeholder="جستجوی نام..."
      class="h-9 text-right placeholder:text-right"
    />
    <div
      class="grid max-h-48 gap-1 overflow-y-auto rounded-lg border p-2"
      :class="disabled ? 'opacity-60' : ''"
    >
      <label
        v-for="u in shown"
        :key="u.id"
        class="flex cursor-pointer items-center gap-2 rounded-md px-2 py-1.5 text-sm hover:bg-muted/50"
      >
        <Checkbox
          :model-value="modelValue.includes(u.id)"
          :disabled="disabled"
          @update:model-value="toggle(u.id)"
        />
        <span class="min-w-0 truncate">{{ u.name }}</span>
        <span
          v-if="u.id === meId"
          class="text-xs text-muted-foreground"
        >(خودم)</span>
      </label>
      <p
        v-if="!shown.length"
        class="p-2 text-center text-xs text-muted-foreground"
      >
        فردی برای انتخاب وجود ندارد.
      </p>
    </div>
    <p class="text-xs text-muted-foreground">
      {{ modelValue.length ? `${toPersianDigits(modelValue.length)} نفر انتخاب شده است.` : 'می‌توانید چند نفر را هم‌زمان انتخاب کنید.' }}
    </p>
  </div>
</template>

<script setup lang="ts">
const props = withDefaults(defineProps<{
  users: { id: string, name: string }[]
  modelValue: string[]
  meId?: string
  disabled?: boolean
}>(), { meId: '', disabled: false })
const emit = defineEmits<{ 'update:modelValue': [value: string[]] }>()

const term = ref('')
const shown = computed(() => {
  const t = term.value.trim().toLowerCase()
  return t ? props.users.filter(u => u.name.toLowerCase().includes(t)) : props.users
})
function toggle(id: string) {
  emit('update:modelValue', props.modelValue.includes(id) ? props.modelValue.filter(x => x !== id) : [...props.modelValue, id])
}
</script>
