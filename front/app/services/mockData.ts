import type {
  Warehouse, StorageLocation, ItemCategory, Unit, Supplier, Employee, InventoryRule,
  Item, InventoryRecord, GoodsReceipt, GoodsIssue, WarehouseTransfer, StockMovement
} from '~/types'

export const warehouses: Warehouse[] = [
  { id: 'wh-1', code: 'WH-AMS', name: 'Amsterdam Central', address: 'Haarlemmerweg 12, Amsterdam', status: 'active' },
  { id: 'wh-2', code: 'WH-RTM', name: 'Rotterdam Port', address: 'Waalhaven 45, Rotterdam', status: 'active' },
  { id: 'wh-3', code: 'WH-UTR', name: 'Utrecht Distribution', address: 'Kanaalweg 8, Utrecht', status: 'active' },
  { id: 'wh-4', code: 'WH-EIN', name: 'Eindhoven Overflow', address: 'De Run 21, Eindhoven', status: 'inactive' }
]

export const locations: StorageLocation[] = [
  { id: 'loc-1', code: 'A-01-01', warehouseId: 'wh-1', name: 'Aisle A, Rack 1, Bin 1', status: 'active' },
  { id: 'loc-2', code: 'A-01-02', warehouseId: 'wh-1', name: 'Aisle A, Rack 1, Bin 2', status: 'active' },
  { id: 'loc-3', code: 'B-02-01', warehouseId: 'wh-1', name: 'Aisle B, Rack 2, Bin 1', status: 'active' },
  { id: 'loc-4', code: 'C-01-01', warehouseId: 'wh-2', name: 'Aisle C, Rack 1, Bin 1', status: 'active' },
  { id: 'loc-5', code: 'C-01-02', warehouseId: 'wh-2', name: 'Aisle C, Rack 1, Bin 2', status: 'active' },
  { id: 'loc-6', code: 'D-01-01', warehouseId: 'wh-3', name: 'Aisle D, Rack 1, Bin 1', status: 'active' }
]

export const categories: ItemCategory[] = [
  { id: 'cat-1', name: 'Electronics', status: 'active' },
  { id: 'cat-2', name: 'Packaging Materials', status: 'active' },
  { id: 'cat-3', name: 'Hand Tools', status: 'active' },
  { id: 'cat-4', name: 'Safety Equipment', status: 'active' },
  { id: 'cat-5', name: 'Raw Materials', status: 'active' }
]

export const units: Unit[] = [
  { id: 'unit-1', code: 'PCS', name: 'Pieces' },
  { id: 'unit-2', code: 'BOX', name: 'Box' },
  { id: 'unit-3', code: 'PLT', name: 'Pallet' },
  { id: 'unit-4', code: 'KG', name: 'Kilogram' },
  { id: 'unit-5', code: 'M', name: 'Meter' }
]

export const suppliers: Supplier[] = [
  { id: 'sup-1', code: 'SUP-001', name: 'NovaTech Components BV', contact: 'Els Bakker', email: 'sales@novatech.example', status: 'active' },
  { id: 'sup-2', code: 'SUP-002', name: 'Rhine Packaging Co.', contact: 'Marco Jansen', email: 'orders@rhinepack.example', status: 'active' },
  { id: 'sup-3', code: 'SUP-003', name: 'Delta Tools Supply', contact: 'Sanne de Groot', email: 'info@deltatools.example', status: 'active' },
  { id: 'sup-4', code: 'SUP-004', name: 'SafeGuard Equipment Ltd.', contact: 'Tom van Dijk', email: 'contact@safeguard.example', status: 'inactive' }
]

export const employees: Employee[] = [
  { id: 'emp-1', name: 'Lucas van der Berg', email: 'l.vandenberg@wms.example', role: 'admin', status: 'active' },
  { id: 'emp-2', name: 'Femke Visser', email: 'f.visser@wms.example', role: 'warehouse_manager', status: 'active' },
  { id: 'emp-3', name: 'Daan Smit', email: 'd.smit@wms.example', role: 'operator', status: 'active' },
  { id: 'emp-4', name: 'Isa Mulder', email: 'i.mulder@wms.example', role: 'operator', status: 'active' },
  { id: 'emp-5', name: 'Ruben de Wit', email: 'r.dewit@wms.example', role: 'viewer', status: 'inactive' }
]

export const inventoryRules: InventoryRule[] = categories.map((c, i) => ({
  id: `rule-${i + 1}`,
  categoryId: c.id,
  minStockDefault: 20,
  reorderPoint: 30,
  requireAdjustmentReason: true
}))

export const items: Item[] = [
  { id: 'itm-1', code: 'ELE-1001', name: 'USB-C Cable 1m', categoryId: 'cat-1', unitId: 'unit-1', status: 'active' },
  { id: 'itm-2', code: 'ELE-1002', name: 'Wireless Barcode Scanner', categoryId: 'cat-1', unitId: 'unit-1', status: 'active' },
  { id: 'itm-3', code: 'PKG-2001', name: 'Corrugated Box 40x30x20', categoryId: 'cat-2', unitId: 'unit-2', status: 'active' },
  { id: 'itm-4', code: 'PKG-2002', name: 'Bubble Wrap Roll 100m', categoryId: 'cat-2', unitId: 'unit-3', status: 'active' },
  { id: 'itm-5', code: 'TLS-3001', name: 'Cordless Drill 18V', categoryId: 'cat-3', unitId: 'unit-1', status: 'active' },
  { id: 'itm-6', code: 'TLS-3002', name: 'Adjustable Wrench Set', categoryId: 'cat-3', unitId: 'unit-1', status: 'active' },
  { id: 'itm-7', code: 'SAF-4001', name: 'Safety Helmet', categoryId: 'cat-4', unitId: 'unit-1', status: 'active' },
  { id: 'itm-8', code: 'SAF-4002', name: 'Hi-Vis Vest', categoryId: 'cat-4', unitId: 'unit-1', status: 'active' },
  { id: 'itm-9', code: 'RAW-5001', name: 'Aluminium Sheet 2mm', categoryId: 'cat-5', unitId: 'unit-4', status: 'active' },
  { id: 'itm-10', code: 'RAW-5002', name: 'Steel Rod 6mm', categoryId: 'cat-5', unitId: 'unit-5', status: 'inactive' }
]

export const inventory: InventoryRecord[] = [
  { id: 'inv-1', itemId: 'itm-1', warehouseId: 'wh-1', locationId: 'loc-1', availableQty: 420, reservedQty: 40, minStock: 100 },
  { id: 'inv-2', itemId: 'itm-2', warehouseId: 'wh-1', locationId: 'loc-2', availableQty: 18, reservedQty: 5, minStock: 25 },
  { id: 'inv-3', itemId: 'itm-3', warehouseId: 'wh-1', locationId: 'loc-3', availableQty: 0, reservedQty: 0, minStock: 50 },
  { id: 'inv-4', itemId: 'itm-4', warehouseId: 'wh-2', locationId: 'loc-4', availableQty: 260, reservedQty: 20, minStock: 60 },
  { id: 'inv-5', itemId: 'itm-5', warehouseId: 'wh-2', locationId: 'loc-5', availableQty: 34, reservedQty: 10, minStock: 40 },
  { id: 'inv-6', itemId: 'itm-6', warehouseId: 'wh-3', locationId: 'loc-6', availableQty: 150, reservedQty: 0, minStock: 30 },
  { id: 'inv-7', itemId: 'itm-7', warehouseId: 'wh-1', locationId: 'loc-1', availableQty: 8, reservedQty: 2, minStock: 20 },
  { id: 'inv-8', itemId: 'itm-8', warehouseId: 'wh-1', locationId: 'loc-2', availableQty: 95, reservedQty: 15, minStock: 40 },
  { id: 'inv-9', itemId: 'itm-9', warehouseId: 'wh-2', locationId: 'loc-4', availableQty: 500, reservedQty: 100, minStock: 200 },
  { id: 'inv-10', itemId: 'itm-10', warehouseId: 'wh-3', locationId: 'loc-6', availableQty: 0, reservedQty: 0, minStock: 50 }
]

export const goodsReceipts: GoodsReceipt[] = [
  { id: 'gr-1', receiptNumber: 'GR-2026-0031', supplierId: 'sup-1', warehouseId: 'wh-1', date: '2026-09-08', status: 'completed', createdBy: 'Daan Smit', lines: [{ id: 'l1', itemId: 'itm-1', quantity: 200 }, { id: 'l2', itemId: 'itm-2', quantity: 20 }] },
  { id: 'gr-2', receiptNumber: 'GR-2026-0032', supplierId: 'sup-2', warehouseId: 'wh-2', date: '2026-09-09', status: 'pending', createdBy: 'Isa Mulder', lines: [{ id: 'l3', itemId: 'itm-4', quantity: 80 }] },
  { id: 'gr-3', receiptNumber: 'GR-2026-0033', supplierId: 'sup-3', warehouseId: 'wh-3', date: '2026-09-07', status: 'completed', createdBy: 'Femke Visser', lines: [{ id: 'l4', itemId: 'itm-6', quantity: 60 }] },
  { id: 'gr-4', receiptNumber: 'GR-2026-0034', supplierId: 'sup-4', warehouseId: 'wh-1', date: '2026-09-06', status: 'cancelled', createdBy: 'Daan Smit', lines: [{ id: 'l5', itemId: 'itm-7', quantity: 30 }] },
  { id: 'gr-5', receiptNumber: 'GR-2026-0035', supplierId: 'sup-1', warehouseId: 'wh-1', date: '2026-09-09', status: 'draft', createdBy: 'Isa Mulder', lines: [{ id: 'l6', itemId: 'itm-1', quantity: 100 }] }
]

export const goodsIssues: GoodsIssue[] = [
  { id: 'gi-1', issueNumber: 'GI-2026-0041', destination: 'Production Line 2', requester: 'Sanne de Groot', warehouseId: 'wh-1', date: '2026-09-09', status: 'completed', lines: [{ id: 'l1', itemId: 'itm-1', quantity: 60 }] },
  { id: 'gi-2', issueNumber: 'GI-2026-0042', destination: 'Client - Rhine Packaging', requester: 'Marco Jansen', warehouseId: 'wh-2', date: '2026-09-08', status: 'pending', lines: [{ id: 'l2', itemId: 'itm-4', quantity: 30 }] },
  { id: 'gi-3', issueNumber: 'GI-2026-0043', destination: 'Retail Store #4', requester: 'Femke Visser', warehouseId: 'wh-3', date: '2026-09-07', status: 'completed', lines: [{ id: 'l3', itemId: 'itm-6', quantity: 12 }] },
  { id: 'gi-4', issueNumber: 'GI-2026-0044', destination: 'Maintenance Dept.', requester: 'Tom van Dijk', warehouseId: 'wh-1', date: '2026-09-05', status: 'cancelled', lines: [{ id: 'l4', itemId: 'itm-8', quantity: 5 }] }
]

export const transfers: WarehouseTransfer[] = [
  { id: 'tr-1', transferNumber: 'TR-2026-0012', itemId: 'itm-1', quantity: 50, sourceWarehouseId: 'wh-1', destinationWarehouseId: 'wh-2', date: '2026-09-08', status: 'completed' },
  { id: 'tr-2', transferNumber: 'TR-2026-0013', itemId: 'itm-6', quantity: 20, sourceWarehouseId: 'wh-3', destinationWarehouseId: 'wh-1', date: '2026-09-09', status: 'in_transit' },
  { id: 'tr-3', transferNumber: 'TR-2026-0014', itemId: 'itm-8', quantity: 15, sourceWarehouseId: 'wh-1', destinationWarehouseId: 'wh-3', date: '2026-09-09', status: 'pending' }
]

export const movements: StockMovement[] = [
  { id: 'mv-1', type: 'inbound', itemId: 'itm-1', warehouseId: 'wh-1', quantity: 200, date: '2026-09-08T09:12:00', reference: 'GR-2026-0031', performedBy: 'Daan Smit' },
  { id: 'mv-2', type: 'outbound', itemId: 'itm-1', warehouseId: 'wh-1', quantity: -60, date: '2026-09-09T10:02:00', reference: 'GI-2026-0041', performedBy: 'Sanne de Groot' },
  { id: 'mv-3', type: 'transfer', itemId: 'itm-1', warehouseId: 'wh-1', quantity: -50, date: '2026-09-08T14:20:00', reference: 'TR-2026-0012', performedBy: 'Femke Visser' },
  { id: 'mv-4', type: 'adjustment', itemId: 'itm-2', warehouseId: 'wh-1', quantity: -3, date: '2026-09-07T16:45:00', reference: 'ADJ-0091', performedBy: 'Isa Mulder', reason: 'Damaged in storage' },
  { id: 'mv-5', type: 'return', itemId: 'itm-8', warehouseId: 'wh-1', quantity: 5, date: '2026-09-06T11:30:00', reference: 'RET-0022', performedBy: 'Daan Smit', reason: 'Customer return - unused' },
  { id: 'mv-6', type: 'reservation', itemId: 'itm-5', warehouseId: 'wh-2', quantity: -10, date: '2026-09-05T08:55:00', reference: 'RES-0071', performedBy: 'Femke Visser' },
  { id: 'mv-7', type: 'release', itemId: 'itm-4', warehouseId: 'wh-2', quantity: 20, date: '2026-09-04T13:10:00', reference: 'REL-0044', performedBy: 'Isa Mulder' }
]
