import { defineStore } from 'pinia'
import type { Transaction } from '~/types/finance'
import { mockTransactions } from '~/utils/mockData'

let nextId = mockTransactions.length + 1

export const useTransactionStore = defineStore('transaction', {
  state: () => ({
    items: [] as Transaction[],
    isLoading: false,
    error: null as string | null,
  }),
  actions: {
    // Replace with `await $fetch('/api/transactions')` once a backend exists.
    async fetchAll() {
      this.isLoading = true
      this.error = null
      try {
        await new Promise((r) => setTimeout(r, 250))
        if (!this.items.length) this.items = mockTransactions
      } catch {
        this.error = 'Failed to load transactions.'
      } finally {
        this.isLoading = false
      }
    },
    async create(payload: Omit<Transaction, 'id' | 'number' | 'status'>) {
      const txn: Transaction = { ...payload, id: `txn-${nextId}`, number: `TXN-${1000 + nextId}`, status: 'confirmed' }
      nextId++
      this.items.unshift(txn)
      return txn
    },
    async update(id: string, payload: Partial<Transaction>) {
      const idx = this.items.findIndex((t) => t.id === id)
      if (idx !== -1) this.items[idx] = { ...this.items[idx], ...payload }
    },
    async remove(id: string) {
      this.items = this.items.filter((t) => t.id !== id)
    },
    byId(id: string) {
      return this.items.find((t) => t.id === id) ?? null
    },
  },
})
