import { defineStore } from 'pinia'
import { inboundApi } from '~/services/api'
import type { GoodsReceipt } from '~/types'

export const useInboundStore = defineStore('inbound', {
  state: () => ({
    receipts: [] as GoodsReceipt[],
    loading: false,
    loaded: false
  }),
  actions: {
    async load(force = false) {
      if (this.loaded && !force) return
      this.loading = true
      this.receipts = await inboundApi.list()
      this.loading = false
      this.loaded = true
    },
    async create(receipt: Omit<GoodsReceipt, 'id' | 'receiptNumber'>) {
      const created = await inboundApi.create(receipt)
      this.receipts.unshift(created)
      return created
    }
  }
})
