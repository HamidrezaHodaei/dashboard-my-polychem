import { defineStore } from 'pinia'
import { outboundApi } from '~/services/api'
import type { GoodsIssue } from '~/types'

export const useOutboundStore = defineStore('outbound', {
  state: () => ({
    issues: [] as GoodsIssue[],
    loading: false,
    loaded: false
  }),
  actions: {
    async load(force = false) {
      if (this.loaded && !force) return
      this.loading = true
      this.issues = await outboundApi.list()
      this.loading = false
      this.loaded = true
    },
    async create(issue: Omit<GoodsIssue, 'id' | 'issueNumber'>) {
      const created = await outboundApi.create(issue)
      this.issues.unshift(created)
      return created
    }
  }
})
