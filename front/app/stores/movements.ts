import { defineStore } from 'pinia'
import { movementApi } from '~/services/api'
import type { StockMovement } from '~/types'

export const useMovementStore = defineStore('movements', {
  state: () => ({
    movements: [] as StockMovement[],
    loading: false,
    loaded: false
  }),
  actions: {
    async load(force = false) {
      if (this.loaded && !force) return
      this.loading = true
      this.movements = await movementApi.list()
      this.loading = false
      this.loaded = true
    }
  }
})
