// ---- Shared domain types -------------------------------------------------

export type PartyType = 'customer' | 'supplier' | 'person' | 'company'

export interface Party {
  id: string
  name: string
  type: PartyType
  phone: string
  mobile: string
  nationalId?: string
  economicCode?: string
  address?: string
  city?: string
  email?: string
  description?: string
  isActive: boolean
  balance: number // positive = they owe us, negative = we owe them
  lastTransactionAt?: string // ISO date
}

export type TransactionType = 'receipt' | 'payment'
export type PaymentMethod = 'cash' | 'card' | 'remittance' | 'bank_transfer' | 'cheque'
export type TransactionStatus = 'confirmed' | 'pending' | 'canceled'

export interface Transaction {
  id: string
  number: string
  type: TransactionType
  partyId: string
  partyName: string
  amount: number
  date: string // ISO
  method: PaymentMethod
  accountId: string
  trackingCode?: string
  invoiceNumber?: string
  description?: string
  attachmentUrl?: string
  status: TransactionStatus
}

export type PurchasePaymentStatus = 'paid' | 'partial' | 'unpaid'

export interface PurchaseItem {
  id: string
  title: string
  quantity: number
  unit: string
  unitPrice: number
}

export interface Purchase {
  id: string
  invoiceNumber: string
  supplierId: string
  supplierName: string
  date: string
  items: PurchaseItem[]
  discount: number
  tax: number
  totalAmount: number // computed: items - discount + tax
  paidAmount: number
  remaining: number // computed: totalAmount - paidAmount
  status: PurchasePaymentStatus
  method: PaymentMethod
  description?: string
  attachmentUrl?: string
}

export type ExpenseCategory =
  | 'salary'
  | 'rent'
  | 'transport'
  | 'electricity'
  | 'water'
  | 'gas'
  | 'internet'
  | 'ads'
  | 'repairs'
  | 'equipment'
  | 'other'

export interface Expense {
  id: string
  title: string
  category: ExpenseCategory
  amount: number
  date: string
  method: PaymentMethod
  accountId: string
  partyId?: string
  description?: string
  attachmentUrl?: string
}

export type AccountType = 'cash' | 'bank' | 'card' | 'foreign_currency'

export interface FinancialAccount {
  id: string
  name: string
  type: AccountType
  accountNumber?: string
  openingBalance: number
  currentBalance: number
  description?: string
  isActive: boolean
}

export interface LedgerEntry {
  id: string
  date: string
  description: string
  debit: number // بدهکار
  credit: number // بستانکار
  balance: number // مانده تجمیعی
}

export interface DashboardSummary {
  cashBalance: number
  bankBalance: number
  totalReceipts: number
  totalPayments: number
  totalCustomerDebt: number
  totalPurchases: number
  totalExpenses: number
  netProfit: number
}

export interface CashFlowPoint {
  label: string
  receipts: number
  payments: number
  net: number
}

export interface ProfitLossPoint {
  label: string
  revenue: number
  expense: number
  profit: number
}
