<!-- <PurchasesFiles v-model="files" :upload :download :max /> : attachments (upload / list / remove / download). -->
<template>
  <div class="space-y-2">
    <ul v-if="modelValue.length" class="space-y-1">
      <li v-for="f in modelValue" :key="f.id" class="flex items-center justify-between rounded-md border px-3 py-1.5 text-sm">
        <button type="button" class="truncate text-primary hover:underline" @click="download(f)">{{ f.name }}</button>
        <button type="button" class="text-xs text-destructive" @click="emit('update:modelValue', modelValue.filter(x => x.id !== f.id))">حذف</button>
      </li>
    </ul>
    <label v-if="modelValue.length < (max || 10)" class="inline-flex cursor-pointer items-center gap-2 rounded-md border border-dashed px-3 py-2 text-sm hover:bg-muted">
      <Icon :name="busy ? 'lucide:loader-circle' : 'lucide:paperclip'" class="size-4" :class="busy && 'animate-spin'" />
      {{ busy ? 'در حال بارگذاری…' : 'افزودن فایل' }}
      <input type="file" class="hidden" :disabled="busy" @change="pick">
    </label>
    <p v-if="error" class="text-xs text-destructive">{{ error }}</p>
  </div>
</template>

<script setup lang="ts">
import type { PFile } from '~/utils/purchase'

const props = defineProps<{ modelValue: PFile[], upload: (f: File) => Promise<PFile>, download: (f: PFile) => Promise<void>, max?: number }>()
const emit = defineEmits<{ (e: 'update:modelValue', v: PFile[]): void }>()
const busy = ref(false)
const error = ref('')
async function pick(ev: Event) {
  const input = ev.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file) return
  busy.value = true
  error.value = ''
  try { emit('update:modelValue', [...props.modelValue, await props.upload(file)]) }
  catch (err: any) { error.value = err?.message || 'بارگذاری فایل انجام نشد.' }
  finally { busy.value = false }
}
</script>
