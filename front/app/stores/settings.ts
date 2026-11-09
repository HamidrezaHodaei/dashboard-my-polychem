import { defineStore } from 'pinia'
import type { CurrencyUnit } from '~/utils/financeFormat'

export const useSettingsStore = defineStore('settings', {
  state: () => ({
    theme: 'light' as 'light' | 'dark',
    sidebarCollapsed: false,
    currencyUnit: 'toman' as CurrencyUnit,
  }),
  actions: {
    toggleTheme() {
      this.theme = this.theme === 'light' ? 'dark' : 'light'
    },
    toggleSidebar() {
      this.sidebarCollapsed = !this.sidebarCollapsed
    },
    setCurrencyUnit(unit: CurrencyUnit) {
      this.currencyUnit = unit
    },
  }
})
