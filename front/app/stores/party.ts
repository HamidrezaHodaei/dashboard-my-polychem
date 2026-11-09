import { defineStore } from 'pinia'
import type { Party } from '~/types/finance'
import { mockParties } from '~/utils/mockData'

let nextId = mockParties.length + 1

export const usePartyStore = defineStore('party', {
  state: () => ({
    items: [] as Party[],
    isLoading: false,
    error: null as string | null,
  }),
  actions: {
    // Replace the mock read with `await $fetch('/api/parties')` once a backend exists.
    async fetchAll() {
      this.isLoading = true
      this.error = null
      try {
        await new Promise((r) => setTimeout(r, 250))
        if (!this.items.length) this.items = mockParties
      } catch {
        this.error = 'Failed to load parties.'
      } finally {
        this.isLoading = false
      }
    },
    async create(payload: Omit<Party, 'id' | 'balance' | 'lastTransactionAt'>) {
      const party: Party = { ...payload, id: `party-${nextId++}`, balance: 0 }
      this.items.unshift(party)
      return party
    },
    async update(id: string, payload: Partial<Party>) {
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
