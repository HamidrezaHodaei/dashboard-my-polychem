import { defineStore } from 'pinia'
import type { FinancialAccount } from '~/types/finance'
import { mockAccounts } from '~/utils/mockData'

let nextId = mockAccounts.length + 1

export const useAccountStore = defineStore('account', {
  state: () => ({
    items: [] as FinancialAccount[],
    isLoading: false,
    error: null as string | null,
  }),
  actions: {
    // Replace with `await $fetch('/api/accounts')` once a backend exists.
    async fetchAll() {
      this.isLoading = true
      this.error = null
      try {
        await new Promise((r) => setTimeout(r, 200))
        if (!this.items.length) this.items = mockAccounts
      } catch {
        this.error = 'Failed to load accounts.'
      } finally {
        this.isLoading = false
      }
    },
    async create(payload: Omit<FinancialAccount, 'id' | 'currentBalance'>) {
      const account: FinancialAccount = { ...payload, id: `acc-${nextId++}`, currentBalance: payload.openingBalance }
      this.items.push(account)
      return account
    },
    async update(id: string, payload: Partial<FinancialAccount>) {
      const idx = this.items.findIndex((a) => a.id === id)
      if (idx !== -1) this.items[idx] = { ...this.items[idx], ...payload }
    },
    async remove(id: string) {
      this.items = this.items.filter((a) => a.id !== id)
    },
    byId(id: string) {
      return this.items.find((a) => a.id === id) ?? null
    },
  },
})
