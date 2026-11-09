import { ref } from 'vue'

interface ConfirmOptions {
  title: string
  description?: string
  confirmLabel?: string
  cancelLabel?: string
  tone?: 'danger' | 'default'
}

// Lightweight app-wide confirm dialog controller. State is module-level (shared by every caller);
// the single host that renders it is <AppConfirmDialog /> in app.vue.
const isOpen = ref(false)
const options = ref<ConfirmOptions>({ title: '' })
let resolver: ((value: boolean) => void) | null = null

export function useConfirm() {
  function confirm(opts: ConfirmOptions): Promise<boolean> {
    resolver?.(false)
    options.value = opts
    isOpen.value = true
    return new Promise((resolve) => { resolver = resolve })
  }

  function resolve(value: boolean) {
    isOpen.value = false
    resolver?.(value)
    resolver = null
  }

  return { isOpen, options, confirm, resolve }
}
