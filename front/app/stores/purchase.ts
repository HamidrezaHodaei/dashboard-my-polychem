import { defineStore } from 'pinia'
import type { Purchase } from '~/types/finance'
import { mockPurchases } from '~/utils/mockData'

let nextId = mockPurchases.length + 1

export const usePurchaseStore = defineStore('purchase', {
  state: () => ({
    items: [] as Purchase[],
    isLoading: false,
    error: null as string | null,
  }),
  actions: {
    // Replace with `await $fetch('/api/purchases')` once a backend exists.
    async fetchAll() {
      this.isLoading = true
      this.error = null
      try {
        await new Promise((r) => setTimeout(r, 250))
        if (!this.items.length) this.items = mockPurchases
      } catch {
        this.error = 'Failed to load purchases.'
      } finally {
        this.isLoading = false
      }
    },
    async create(payload: Omit<Purchase, 'id' | 'invoiceNumber'>) {
      const purchase: Purchase = { ...payload, id: `purchase-${nextId}`, invoiceNumber: `PUR-${3000 + nextId}` }
      nextId++
      this.items.unshift(purchase)
      return purchase
    },
    async update(id: string, payload: Partial<Purchase>) {
      const idx = this.items.findIndex((p) => p.id === id)
      if (idx !== -1) this.items[idx] = { ...this.items[idx], ...payload }
    },
    async remove(id: string) {
      this.items = this.items.filter((p) => p.id !== id)
    },
    byId(id: string) {
      return this.items.find((p) => p.id === id) ?? null
    },
  },
})
