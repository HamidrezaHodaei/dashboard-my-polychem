import { defineStore } from 'pinia'

// Stage 7 & 8: profit/loss + cash-flow report state, backed by
// `$fetch('/api/reports/profit-loss')` and `$fetch('/api/reports/cash-flow')`.
export const useReportStore = defineStore('report', {
  state: () => ({ isLoading: false }),
  actions: {},
})
