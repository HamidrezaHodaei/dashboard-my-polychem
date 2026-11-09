import { defineStore } from 'pinia'

// Renamed from `ToastItem` -- that name collided with composables/useToast.ts's
// (unrelated) Finance-module toast type and caused a Nuxt duplicate-import
// warning; nothing outside this file referenced this type by name.
export interface WmsToastItem {
  id: string
  title: string
  description?: string
  tone: 'success' | 'danger' | 'info'
}

export const useToastStore = defineStore('toast', {
  state: () => ({
    items: [] as WmsToastItem[]
  }),
  actions: {
    push(item: Omit<WmsToastItem, 'id'>) {
      const id = `toast-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`
      this.items.push({ ...item, id })
      setTimeout(() => this.dismiss(id), 4200)
    },
    dismiss(id: string) {
      this.items = this.items.filter((t) => t.id !== id)
    },
    success(title: string, description?: string) { this.push({ title, description, tone: 'success' }) },
    error(title: string, description?: string) { this.push({ title, description, tone: 'danger' }) },
    info(title: string, description?: string) { this.push({ title, description, tone: 'info' }) }
  }
})
