import { defineStore } from 'pinia'
import { transferApi } from '~/services/api'
import type { WarehouseTransfer } from '~/types'

export const useTransferStore = defineStore('transfers', {
  state: () => ({
    transfers: [] as WarehouseTransfer[],
    loading: false,
    loaded: false
  }),
  actions: {
    async load(force = false) {
      if (this.loaded && !force) return
      this.loading = true
      this.transfers = await transferApi.list()
      this.loading = false
      this.loaded = true
    },
    async create(t: Omit<WarehouseTransfer, 'id' | 'transferNumber'>) {
      const created = await transferApi.create(t)
      this.transfers.unshift(created)
      return created
    }
  }
})
