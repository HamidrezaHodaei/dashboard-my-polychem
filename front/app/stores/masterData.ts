import { defineStore } from 'pinia'
import {
  warehouseApi, locationApi, categoryApi, unitApi, supplierApi, employeeApi, inventoryRuleApi, itemApi
} from '~/services/api'
import type {
  Warehouse, StorageLocation, ItemCategory, Unit, Supplier, Employee, InventoryRule, Item
} from '~/types'

export const useMasterDataStore = defineStore('masterData', {
  state: () => ({
    warehouses: [] as Warehouse[],
    locations: [] as StorageLocation[],
    categories: [] as ItemCategory[],
    units: [] as Unit[],
    suppliers: [] as Supplier[],
    employees: [] as Employee[],
    rules: [] as InventoryRule[],
    items: [] as Item[],
    loaded: false,
    loading: false
  }),
  getters: {
    activeWarehouses: (state) => state.warehouses.filter((w) => w.status === 'active'),
    activeItems: (state) => state.items.filter((i) => i.status === 'active'),
    warehouseName: (state) => (id: string) => state.warehouses.find((w) => w.id === id)?.name ?? '—',
    itemByCode: (state) => (id: string) => state.items.find((i) => i.id === id),
    categoryName: (state) => (id: string) => state.categories.find((c) => c.id === id)?.name ?? '—',
    supplierName: (state) => (id: string) => state.suppliers.find((s) => s.id === id)?.name ?? '—'
  },
  actions: {
    async loadAll() {
      if (this.loaded) return
      this.loading = true
      const [warehouses, locations, categories, units, suppliers, employees, rules, items] = await Promise.all([
        warehouseApi.list(), locationApi.list(), categoryApi.list(), unitApi.list(),
        supplierApi.list(), employeeApi.list(), inventoryRuleApi.list(), itemApi.list()
      ])
      this.warehouses = warehouses
      this.locations = locations
      this.categories = categories
      this.units = units
      this.suppliers = suppliers
      this.employees = employees
      this.rules = rules
      this.items = items
      this.loaded = true
      this.loading = false
    },
    async saveWarehouse(w: Warehouse) {
      const saved = await warehouseApi.save(w)
      const idx = this.warehouses.findIndex((x) => x.id === saved.id)
      if (idx >= 0) this.warehouses[idx] = saved
      else this.warehouses.push(saved)
    },
    async saveSupplier(s: Supplier) {
      const saved = await supplierApi.save(s)
      const idx = this.suppliers.findIndex((x) => x.id === saved.id)
      if (idx >= 0) this.suppliers[idx] = saved
      else this.suppliers.push(saved)
    },
    async saveEmployee(e: Employee) {
      const saved = await employeeApi.save(e)
      const idx = this.employees.findIndex((x) => x.id === saved.id)
      if (idx >= 0) this.employees[idx] = saved
      else this.employees.push(saved)
    },
    async saveItem(item: Item) {
      const saved = await itemApi.save(item)
      const idx = this.items.findIndex((x) => x.id === saved.id)
      if (idx >= 0) this.items[idx] = saved
      else this.items.push(saved)
    },
    saveCategory(category: ItemCategory) {
      const idx = this.categories.findIndex((x) => x.id === category.id)
      if (idx >= 0) this.categories[idx] = category
      else this.categories.push(category)
    },
    saveUnit(unit: Unit) {
      const idx = this.units.findIndex((x) => x.id === unit.id)
      if (idx >= 0) this.units[idx] = unit
      else this.units.push(unit)
    },
    saveLocation(location: StorageLocation) {
      const idx = this.locations.findIndex((x) => x.id === location.id)
      if (idx >= 0) this.locations[idx] = location
      else this.locations.push(location)
    }
  }
})
