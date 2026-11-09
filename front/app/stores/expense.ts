import { defineStore } from 'pinia'
import type { Expense } from '~/types/finance'
import { mockExpenses } from '~/utils/mockData'

let nextId = mockExpenses.length + 1

export const useExpenseStore = defineStore('expense', {
  state: () => ({
    items: [] as Expense[],
    isLoading: false,
    error: null as string | null,
  }),
  actions: {
    // Replace with `await $fetch('/api/expenses')` once a backend exists.
    async fetchAll() {
      this.isLoading = true
      this.error = null
      try {
        await new Promise((r) => setTimeout(r, 250))
        if (!this.items.length) this.items = mockExpenses
      } catch {
        this.error = 'Failed to load expenses.'
      } finally {
        this.isLoading = false
      }
    },
    async create(payload: Omit<Expense, 'id'>) {
      const expense: Expense = { ...payload, id: `expense-${nextId++}` }
      this.items.unshift(expense)
      return expense
    },
    async update(id: string, payload: Partial<Expense>) {
      const idx = this.items.findIndex((e) => e.id === id)
      if (idx !== -1) this.items[idx] = { ...this.items[idx], ...payload }
    },
    async remove(id: string) {
      this.items = this.items.filter((e) => e.id !== id)
    },
    byId(id: string) {
      return this.items.find((e) => e.id === id) ?? null
    },
  },
})
