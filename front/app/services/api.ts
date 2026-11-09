import * as db from './mockData'
import type {
  Warehouse, StorageLocation, ItemCategory, Unit, Supplier, Employee, InventoryRule,
  Item, InventoryRecord, InventoryRow, GoodsReceipt, GoodsIssue, WarehouseTransfer,
  StockMovement, StockAdjustment
} from '~/types'

// Simulated network latency so loading states are meaningful during development.
const delay = (ms = 250) => new Promise((r) => setTimeout(r, ms))

function computeStockStatus(row: { availableQty: number; minStock: number }): InventoryRow['stockStatus'] {
  if (row.availableQty <= 0) return 'out_of_stock'
  if (row.availableQty <= row.minStock) return 'low_stock'
  return 'in_stock'
}

function toInventoryRow(rec: InventoryRecord): InventoryRow {
  const item = db.items.find((i) => i.id === rec.itemId)!
  const wh = db.warehouses.find((w) => w.id === rec.warehouseId)!
  const loc = db.locations.find((l) => l.id === rec.locationId)!
  const cat = db.categories.find((c) => c.id === item.categoryId)!
  const unit = db.units.find((u) => u.id === item.unitId)!
  return {
    ...rec,
    itemCode: item.code,
    itemName: item.name,
    categoryName: cat.name,
    warehouseName: wh.name,
    locationCode: loc.code,
    unitCode: unit.code,
    stockStatus: computeStockStatus(rec)
  }
}

// ---------------- Inventory ----------------
export const inventoryApi = {
  async list(): Promise<InventoryRow[]> {
    await delay()
    return db.inventory.map(toInventoryRow)
  },
  async adjust(input: Omit<StockAdjustment, 'id' | 'date'>): Promise<InventoryRow> {
    await delay(200)
    const rec = db.inventory.find((r) => r.itemId === input.itemId && r.warehouseId === input.warehouseId)
    if (!rec) throw new Error('Inventory record not found')
    rec.availableQty = Math.max(0, rec.availableQty + input.quantityDelta)
    db.movements.unshift({
      id: `mv-${Date.now()}`,
      type: 'adjustment',
      itemId: input.itemId,
      warehouseId: input.warehouseId,
      quantity: input.quantityDelta,
      date: new Date().toISOString(),
      reference: `ADJ-${Math.floor(Math.random() * 9000 + 1000)}`,
      performedBy: input.performedBy,
      reason: input.reason
    })
    return toInventoryRow(rec)
  }
}

// ---------------- Master data ----------------
export const warehouseApi = {
  async list(): Promise<Warehouse[]> { await delay(150); return [...db.warehouses] },
  async save(w: Warehouse) {
    await delay(150)
    const idx = db.warehouses.findIndex((x) => x.id === w.id)
    if (idx >= 0) db.warehouses[idx] = w
    else db.warehouses.push({ ...w, id: `wh-${Date.now()}` })
    return w
  }
}

export const locationApi = {
  async list(): Promise<StorageLocation[]> { await delay(150); return [...db.locations] }
}

export const categoryApi = {
  async list(): Promise<ItemCategory[]> { await delay(150); return [...db.categories] }
}

export const unitApi = {
  async list(): Promise<Unit[]> { await delay(150); return [...db.units] }
}

export const supplierApi = {
  async list(): Promise<Supplier[]> { await delay(150); return [...db.suppliers] },
  async save(s: Supplier) {
    await delay(150)
    const idx = db.suppliers.findIndex((x) => x.id === s.id)
    if (idx >= 0) db.suppliers[idx] = s
    else db.suppliers.push({ ...s, id: `sup-${Date.now()}` })
    return s
  }
}

export const employeeApi = {
  async list(): Promise<Employee[]> { await delay(150); return [...db.employees] },
  async save(e: Employee) {
    await delay(150)
    const idx = db.employees.findIndex((x) => x.id === e.id)
    if (idx >= 0) db.employees[idx] = e
    else db.employees.push({ ...e, id: `emp-${Date.now()}` })
    return e
  }
}

export const inventoryRuleApi = {
  async list(): Promise<InventoryRule[]> { await delay(150); return [...db.inventoryRules] }
}

export const itemApi = {
  async list(): Promise<Item[]> { await delay(150); return [...db.items] },
  async save(item: Item) {
    await delay(150)
    const idx = db.items.findIndex((x) => x.id === item.id)
    if (idx >= 0) db.items[idx] = item
    else db.items.push({ ...item, id: `itm-${Date.now()}` })
    return item
  }
}

// ---------------- Inbound ----------------
export const inboundApi = {
  async list(): Promise<GoodsReceipt[]> { await delay(); return [...db.goodsReceipts] },
  async create(receipt: Omit<GoodsReceipt, 'id' | 'receiptNumber'>): Promise<GoodsReceipt> {
    await delay(300)
    const created: GoodsReceipt = {
      ...receipt,
      id: `gr-${Date.now()}`,
      receiptNumber: `GR-2026-${String(1000 + db.goodsReceipts.length + 1).slice(-4)}`
    }
    db.goodsReceipts.unshift(created)
    if (created.status === 'completed') {
      for (const line of created.lines) {
        const rec = db.inventory.find((r) => r.itemId === line.itemId && r.warehouseId === created.warehouseId)
        if (rec) rec.availableQty += line.quantity
        db.movements.unshift({
          id: `mv-${Date.now()}-${line.id}`, type: 'inbound', itemId: line.itemId,
          warehouseId: created.warehouseId, quantity: line.quantity, date: created.date,
          reference: created.receiptNumber, performedBy: created.createdBy
        })
      }
    }
    return created
  }
}

// ---------------- Outbound ----------------
export const outboundApi = {
  async list(): Promise<GoodsIssue[]> { await delay(); return [...db.goodsIssues] },
  async create(issue: Omit<GoodsIssue, 'id' | 'issueNumber'>): Promise<GoodsIssue> {
    await delay(300)
    const created: GoodsIssue = {
      ...issue,
      id: `gi-${Date.now()}`,
      issueNumber: `GI-2026-${String(1000 + db.goodsIssues.length + 1).slice(-4)}`
    }
    db.goodsIssues.unshift(created)
    if (created.status === 'completed') {
      for (const line of created.lines) {
        const rec = db.inventory.find((r) => r.itemId === line.itemId && r.warehouseId === created.warehouseId)
        if (rec) rec.availableQty = Math.max(0, rec.availableQty - line.quantity)
        db.movements.unshift({
          id: `mv-${Date.now()}-${line.id}`, type: 'outbound', itemId: line.itemId,
          warehouseId: created.warehouseId, quantity: -line.quantity, date: created.date,
          reference: created.issueNumber, performedBy: created.requester
        })
      }
    }
    return created
  }
}

// ---------------- Transfers ----------------
export const transferApi = {
  async list(): Promise<WarehouseTransfer[]> { await delay(); return [...db.transfers] },
  async create(t: Omit<WarehouseTransfer, 'id' | 'transferNumber'>): Promise<WarehouseTransfer> {
    if (t.sourceWarehouseId === t.destinationWarehouseId) {
      throw new Error('Source and destination warehouse cannot be the same.')
    }
    const rec = db.inventory.find((r) => r.itemId === t.itemId && r.warehouseId === t.sourceWarehouseId)
    if (!rec || rec.availableQty < t.quantity) {
      throw new Error('Transfer quantity exceeds available stock at source warehouse.')
    }
    await delay(300)
    const created: WarehouseTransfer = {
      ...t,
      id: `tr-${Date.now()}`,
      transferNumber: `TR-2026-${String(1000 + db.transfers.length + 1).slice(-4)}`
    }
    db.transfers.unshift(created)
    rec.availableQty -= t.quantity
    db.movements.unshift({
      id: `mv-${Date.now()}`, type: 'transfer', itemId: t.itemId, warehouseId: t.sourceWarehouseId,
      quantity: -t.quantity, date: created.date, reference: created.transferNumber, performedBy: 'System'
    })
    return created
  }
}

// ---------------- Movements ----------------
export const movementApi = {
  async list(): Promise<StockMovement[]> { await delay(); return [...db.movements] }
}

// ---------------- Dashboard ----------------
export const dashboardApi = {
  async kpis() {
    await delay(200)
    const rows = db.inventory.map(toInventoryRow)
    const today = new Date().toISOString().slice(0, 10)
    return {
      totalItems: db.items.filter((i) => i.status === 'active').length,
      totalStock: rows.reduce((sum, r) => sum + r.availableQty, 0),
      lowStock: rows.filter((r) => r.stockStatus === 'low_stock').length,
      outOfStock: rows.filter((r) => r.stockStatus === 'out_of_stock').length,
      todayInbound: db.goodsReceipts.filter((g) => g.date === today).length,
      todayOutbound: db.goodsIssues.filter((g) => g.date === today).length,
      pendingTransfers: db.transfers.filter((t) => t.status === 'pending' || t.status === 'in_transit').length,
      stockValue: rows.reduce((sum, r) => sum + r.availableQty * 12.5, 0)
    }
  }
}
