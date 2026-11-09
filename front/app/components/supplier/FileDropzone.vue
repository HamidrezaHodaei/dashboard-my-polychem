<!-- /components/supplier/FileDropzone.vue  → <SupplierFileDropzone /> -->
<!--
  Upload target that accepts files three ways:
    1. click → native file picker
    2. drag & drop onto the box
    3. paste (Ctrl/⌘+V) while the box is hovered or focused — works for files
       copied in the file manager and for screenshots / copied images.
  It only emits the raw File[]; validation + upload stay with the parent.
-->
<template>
  <div
    role="button"
    tabindex="0"
    class="flex cursor-pointer items-center gap-3 rounded-lg border-2 border-dashed px-4 py-3 text-sm outline-none transition-colors focus-visible:ring-2 focus-visible:ring-ring"
    :class="[
      dragging ? 'border-primary bg-primary/5' : 'border-border hover:border-muted-foreground/50 hover:bg-muted/30',
      invalid && !dragging ? 'border-destructive' : '',
      disabled ? 'pointer-events-none opacity-50' : '',
    ]"
    :aria-disabled="disabled"
    @click="openPicker"
    @keydown.enter.prevent="openPicker"
    @keydown.space.prevent="openPicker"
    @dragenter.prevent="onDragEnter"
    @dragover.prevent="onDragOver"
    @dragleave="onDragLeave"
    @drop.prevent="onDrop"
    @mouseenter="hovered = true"
    @mouseleave="hovered = false"
    @focus="focused = true"
    @blur="focused = false"
  >
    <Icon
      :name="loading ? 'lucide:loader-circle' : icon"
      class="size-5 shrink-0 text-muted-foreground"
      :class="{ 'animate-spin': loading }"
    />
    <span class="min-w-0 flex-1">
      <span class="block font-medium">{{ loading ? 'در حال بارگذاری...' : label }}</span>
      <span class="block text-xs text-muted-foreground">
        {{ dragging ? 'برای بارگذاری رها کنید' : 'بکشید و رها کنید، یا اینجا کلیک کنید و Ctrl+V بزنید' }}
      </span>
    </span>
    <input
      ref="input"
      type="file"
      class="sr-only"
      tabindex="-1"
      :multiple="multiple"
      :accept="accept"
      :disabled="disabled"
      @click.stop
      @change="onPick"
    >
  </div>
</template>

<script setup lang="ts">
const props = withDefaults(defineProps<{
  label: string
  icon?: string
  accept?: string
  multiple?: boolean
  disabled?: boolean
  loading?: boolean
  invalid?: boolean
}>(), { icon: 'lucide:upload', accept: undefined, multiple: false, disabled: false, loading: false, invalid: false })

const emit = defineEmits<{ files: [files: File[]] }>()

const input = ref<HTMLInputElement | null>(null)
const dragging = ref(false)
const hovered = ref(false)
const focused = ref(false)
let depth = 0 // dragenter/leave fire for child elements too

function deliver(list: File[]) {
  if (props.disabled || props.loading || !list.length) return
  emit('files', props.multiple ? list : list.slice(0, 1))
}

function openPicker() {
  if (!props.disabled) input.value?.click()
}
function onPick(e: Event) {
  const el = e.target as HTMLInputElement
  const list = [...(el.files ?? [])]
  el.value = '' // picking the same file twice must still fire change
  deliver(list)
}

function hasFiles(e: DragEvent) {
  return [...(e.dataTransfer?.types ?? [])].includes('Files')
}
function onDragEnter(e: DragEvent) {
  if (!hasFiles(e)) return
  depth++
  dragging.value = true
}
function onDragOver(e: DragEvent) {
  if (e.dataTransfer && hasFiles(e)) e.dataTransfer.dropEffect = 'copy'
}
function onDragLeave() {
  depth = Math.max(0, depth - 1)
  if (!depth) dragging.value = false
}
function onDrop(e: DragEvent) {
  depth = 0
  dragging.value = false
  deliver([...(e.dataTransfer?.files ?? [])])
}

// Screenshots arrive as a generic "image.png"; give each a unique name.
function nameClipboardFile(f: File, i: number) {
  if (!/^image\.\w+$/i.test(f.name)) return f
  const ext = f.name.split('.').pop()
  return new File([f], `pasted-${Date.now()}-${i + 1}.${ext}`, { type: f.type })
}

// One document-level listener: acts only while this box is hovered/focused,
// and never steals a paste meant for a text field elsewhere on the form.
function onPaste(e: ClipboardEvent) {
  if (!(hovered.value || focused.value) || props.disabled) return
  const target = e.target as HTMLElement | null
  const typing = !!target?.closest('input:not([type=file]), textarea, [contenteditable=true]')
  if (typing) return
  const list = [...(e.clipboardData?.files ?? [])]
  if (!list.length) return
  e.preventDefault()
  deliver(list.map(nameClipboardFile))
}
onMounted(() => document.addEventListener('paste', onPaste))
onBeforeUnmount(() => document.removeEventListener('paste', onPaste))
</script>