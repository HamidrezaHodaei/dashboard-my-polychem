// ---------- Shared ----------
export type Status = 'active' | 'inactive'

export type BadgeTone = 'neutral' | 'success' | 'danger' | 'warn' | 'info' | 'amber'

export interface SelectOption {
  label: string
  value: string
}

// ---------- Master data ----------
export interface Warehouse {
  id: string
  code: string
  name: string
  address: string
  status: Status
}

export interface StorageLocation {
  id: string
  code: string
  warehouseId: string
  name: string
  status: Status
}

export interface ItemCategory {
  id: string
  name: string
  status: Status
}

export interface Unit {
  id: string
  code: string
  name: string
}

export interface Supplier {
  id: string
  code: string
  name: string
  contact: string
  email: string
  status: Status
}

export type EmployeeRole = 'admin' | 'warehouse_manager' | 'operator' | 'viewer'

export interface Employee {
  id: string
  name: string
  email: string
  role: EmployeeRole
  status: Status
}

export interface InventoryRule {
  id: string
  categoryId: string
  minStockDefault: number
  reorderPoint: number
  requireAdjustmentReason: boolean
}

// ---------- Items & Inventory ----------
export interface Item {
  id: string
  code: string
  name: string
  categoryId: string
  unitId: string
  status: Status
}

export interface InventoryRecord {
  id: string
  itemId: string
  warehouseId: string
  locationId: string
  availableQty: number
  reservedQty: number
  minStock: number
}

// Denormalized row used by the Inventory table / UI
export interface InventoryRow extends InventoryRecord {
  itemCode: string
  itemName: string
  categoryName: string
  warehouseName: string
  locationCode: string
  unitCode: string
  stockStatus: 'in_stock' | 'low_stock' | 'out_of_stock'
}

// ---------- Inbound ----------
export type DocumentStatus = 'draft' | 'pending' | 'completed' | 'cancelled'

export interface ReceiptLine {
  id: string
  itemId: string
  quantity: number
}

export interface GoodsReceipt {
  id: string
  receiptNumber: string
  supplierId: string
  warehouseId: string
  date: string
  lines: ReceiptLine[]
  status: DocumentStatus
  createdBy: string
}

// ---------- Outbound ----------
export interface IssueLine {
  id: string
  itemId: string
  quantity: number
}

export interface GoodsIssue {
  id: string
  issueNumber: string
  destination: string
  requester: string
  warehouseId: string
  date: string
  lines: IssueLine[]
  status: DocumentStatus
}

// ---------- Transfers ----------
export type TransferStatus = 'pending' | 'in_transit' | 'completed' | 'cancelled'

export interface WarehouseTransfer {
  id: string
  transferNumber: string
  itemId: string
  quantity: number
  sourceWarehouseId: string
  destinationWarehouseId: string
  date: string
  status: TransferStatus
  note?: string
}

// ---------- Stock movements ----------
export type MovementType =
  | 'inbound'
  | 'outbound'
  | 'transfer'
  | 'adjustment'
  | 'return'
  | 'reservation'
  | 'release'

export interface StockMovement {
  id: string
  type: MovementType
  itemId: string
  warehouseId: string
  quantity: number
  date: string
  reference: string
  performedBy: string
  reason?: string
}

// ---------- Stock adjustment ----------
export interface StockAdjustment {
  id: string
  itemId: string
  warehouseId: string
  locationId: string
  quantityDelta: number
  reason: string
  date: string
  performedBy: string
}

// ---------- Table / pagination ----------
export interface TableColumn<T = any> {
  key: string
  label: string
  align?: 'left' | 'right' | 'center'
  width?: string
  formatter?: (row: T) => string
}
