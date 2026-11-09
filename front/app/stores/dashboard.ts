import { defineStore } from 'pinia'
import type { DashboardSummary, CashFlowPoint, ProfitLossPoint, Transaction } from '~/types/finance'
import { dashboardSummary, cashFlowWeekly, profitLossMonthly, mockTransactions } from '~/utils/mockData'

interface DashboardState {
  summary: DashboardSummary | null
  cashFlow: CashFlowPoint[]
  profitLoss: ProfitLossPoint[]
  recentTransactions: Transaction[]
  isLoading: boolean
  error: string | null
}

export const useDashboardStore = defineStore('dashboard', {
  state: (): DashboardState => ({
    summary: null,
    cashFlow: [],
    profitLoss: [],
    recentTransactions: [],
    isLoading: false,
    error: null,
  }),
  actions: {
    /**
     * Loads dashboard data. Currently backed by mock data; replace the body
     * with real `$fetch('/api/dashboard')` calls once the backend exists —
     * the store's public shape (state + this action) doesn't need to change.
     */
    async fetchDashboard() {
      this.isLoading = true
      this.error = null
      try {
        await new Promise((resolve) => setTimeout(resolve, 400)) // simulate network
        this.summary = dashboardSummary
        this.cashFlow = cashFlowWeekly
        this.profitLoss = profitLossMonthly
        this.recentTransactions = mockTransactions.slice(0, 8)
      } catch (e) {
        this.error = 'Failed to load dashboard data.'
      } finally {
        this.isLoading = false
      }
    },
  },
})
