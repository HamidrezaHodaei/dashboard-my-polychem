import { defineStore } from 'pinia'
import { inventoryApi } from '~/services/api'
import type { InventoryRow, StockAdjustment } from '~/types'

export const useInventoryStore = defineStore('inventory', {
  state: () => ({
    rows: [] as InventoryRow[],
    loading: false,
    loaded: false
  }),
  getters: {
    lowStockCount: (state) => state.rows.filter((r) => r.stockStatus === 'low_stock').length,
    outOfStockCount: (state) => state.rows.filter((r) => r.stockStatus === 'out_of_stock').length
  },
  actions: {
    async load(force = false) {
      if (this.loaded && !force) return
      this.loading = true
      this.rows = await inventoryApi.list()
      this.loading = false
      this.loaded = true
    },
    async adjust(input: Omit<StockAdjustment, 'id' | 'date'>) {
      const updated = await inventoryApi.adjust(input)
      const idx = this.rows.findIndex((r) => r.itemId === updated.itemId && r.warehouseId === updated.warehouseId)
      if (idx >= 0) this.rows[idx] = updated
    }
  }
})
