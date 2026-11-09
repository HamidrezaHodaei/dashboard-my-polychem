import type {
  Party, Transaction, Purchase, Expense, FinancialAccount,
  DashboardSummary, CashFlowPoint, ProfitLossPoint,
} from '~/types/finance'

export const mockAccounts: FinancialAccount[] = [
  { id: 'acc-1', name: 'Main cash', type: 'cash', openingBalance: 20_000_000, currentBalance: 34_500_000, isActive: true },
  { id: 'acc-2', name: 'Mellat Bank', accountNumber: '1234-5678-90', type: 'bank', openingBalance: 80_000_000, currentBalance: 121_300_000, isActive: true },
  { id: 'acc-3', name: 'Melli Bank', accountNumber: '0987-6543-21', type: 'bank', openingBalance: 40_000_000, currentBalance: 22_150_000, isActive: true },
  { id: 'acc-4', name: 'Card account', type: 'card', openingBalance: 5_000_000, currentBalance: 8_760_000, isActive: true },
  { id: 'acc-5', name: 'Foreign currency account', type: 'foreign_currency', openingBalance: 0, currentBalance: 1_200_000, isActive: false },
]

const partyNames = [
  'Aria Store', 'Parsian Trade Co.', 'Ali Mohammadi', 'Novin Trading', 'Sara Ahmadi',
  'Employee Consumer Cooperative', 'Alborz Steel Co.', 'Reza Karimi', 'Refah Chain Store',
  'Sepehr Distribution Co.', 'Maryam Hosseini', 'Iran Wood Industries', 'Hossein Rezaei', 'Golestan Trading Co.',
  'Fatemeh Nouri',
]

export const mockParties: Party[] = partyNames.map((name, i) => {
  const types: Party['type'][] = ['customer', 'supplier', 'person', 'company']
  const type = types[i % types.length]
  const balance = Math.round((Math.random() - 0.4) * 20_000_000)
  return {
    id: `party-${i + 1}`,
    name,
    type,
    phone: `021-${8800 + i}0000`,
    mobile: `0912${(1000000 + i * 1234).toString().slice(0, 7)}`,
    nationalId: type === 'company' ? `1400${100000 + i}` : `00${1000000 + i}`,
    economicCode: type === 'company' || type === 'supplier' ? `${411000000 + i}` : undefined,
    address: 'Valiasr Street, Tehran',
    city: 'Tehran',
    email: `contact${i + 1}@example.com`,
    isActive: i % 7 !== 0,
    balance,
    lastTransactionAt: new Date(Date.now() - i * 86_400_000).toISOString(),
  }
})

const methods: Transaction['method'][] = ['cash', 'card', 'remittance', 'bank_transfer', 'cheque']

export const mockTransactions: Transaction[] = Array.from({ length: 20 }, (_, i) => {
  const party = mockParties[i % mockParties.length]
  const type: Transaction['type'] = i % 3 === 0 ? 'payment' : 'receipt'
  return {
    id: `txn-${i + 1}`,
    number: `TXN-${1000 + i}`,
    type,
    partyId: party.id,
    partyName: party.name,
    amount: 500_000 + Math.round(Math.random() * 9_500_000),
    date: new Date(Date.now() - i * 43_200_000).toISOString(),
    method: methods[i % methods.length],
    accountId: mockAccounts[i % mockAccounts.length].id,
    trackingCode: `${900000 + i}`,
    invoiceNumber: i % 2 === 0 ? `INV-${2000 + i}` : undefined,
    description: type === 'receipt' ? 'Receipt for sales invoice' : 'Payment for account settlement',
    status: i % 9 === 0 ? 'pending' : 'confirmed',
  }
})

export const mockPurchases: Purchase[] = Array.from({ length: 10 }, (_, i) => {
  const supplier = mockParties.filter((p) => p.type === 'supplier')[i % 4] ?? mockParties[i]
  const items = [
    { id: `item-${i}-1`, title: 'A4 paper', quantity: 20, unit: 'pack', unitPrice: 350_000 },
    { id: `item-${i}-2`, title: 'Printer ink', quantity: 5, unit: 'piece', unitPrice: 620_000 },
  ]
  const itemsTotal = items.reduce((s, it) => s + it.quantity * it.unitPrice, 0)
  const discount = Math.round(itemsTotal * 0.03)
  const tax = Math.round((itemsTotal - discount) * 0.09)
  const totalAmount = itemsTotal - discount + tax
  const paidAmount = i % 3 === 0 ? totalAmount : i % 3 === 1 ? Math.round(totalAmount * 0.5) : 0
  const remaining = totalAmount - paidAmount
  return {
    id: `purchase-${i + 1}`,
    invoiceNumber: `PUR-${3000 + i}`,
    supplierId: supplier.id,
    supplierName: supplier.name,
    date: new Date(Date.now() - i * 3 * 86_400_000).toISOString(),
    items,
    discount,
    tax,
    totalAmount,
    paidAmount,
    remaining,
    status: remaining === 0 ? 'paid' : paidAmount === 0 ? 'unpaid' : 'partial',
    method: methods[i % methods.length],
  }
})

const expenseCategories: Expense['category'][] = [
  'salary', 'rent', 'transport', 'electricity', 'water', 'gas', 'internet', 'ads', 'repairs', 'equipment',
]
const expenseTitles: Record<Expense['category'], string> = {
  salary: 'Staff salaries', rent: 'Office rent', transport: 'Transportation', electricity: 'Electricity bill',
  water: 'Water bill', gas: 'Gas bill', internet: 'Internet', ads: 'Social media advertising',
  repairs: 'Equipment repairs', equipment: 'Office equipment', other: 'Other expenses',
}

export const mockExpenses: Expense[] = expenseCategories.map((category, i) => ({
  id: `expense-${i + 1}`,
  title: expenseTitles[category],
  category,
  amount: 400_000 + Math.round(Math.random() * 12_000_000),
  date: new Date(Date.now() - i * 2 * 86_400_000).toISOString(),
  method: methods[i % methods.length],
  accountId: mockAccounts[i % mockAccounts.length].id,
}))

export const mockCustomers = mockParties.filter((p) => p.type === 'customer')

export const dashboardSummary: DashboardSummary = {
  cashBalance: mockAccounts.filter((a) => a.type === 'cash').reduce((s, a) => s + a.currentBalance, 0),
  bankBalance: mockAccounts.filter((a) => a.type === 'bank').reduce((s, a) => s + a.currentBalance, 0),
  totalReceipts: mockTransactions.filter((t) => t.type === 'receipt').reduce((s, t) => s + t.amount, 0),
  totalPayments: mockTransactions.filter((t) => t.type === 'payment').reduce((s, t) => s + t.amount, 0),
  totalCustomerDebt: mockParties.filter((p) => p.balance > 0).reduce((s, p) => s + p.balance, 0),
  totalPurchases: mockPurchases.reduce((s, p) => s + p.totalAmount, 0),
  totalExpenses: mockExpenses.reduce((s, e) => s + e.amount, 0),
  netProfit: 0,
}
dashboardSummary.netProfit =
  dashboardSummary.totalReceipts - dashboardSummary.totalPayments -
  dashboardSummary.totalExpenses - dashboardSummary.totalPurchases * 0.2

const weekdayLabels = ['شنبه', 'یک‌شنبه', 'دوشنبه', 'سه‌شنبه', 'چهارشنبه', 'پنج‌شنبه', 'جمعه']

export const cashFlowWeekly: CashFlowPoint[] = weekdayLabels.map((label) => {
  const receipts = 2_000_000 + Math.round(Math.random() * 8_000_000)
  const payments = 1_000_000 + Math.round(Math.random() * 6_000_000)
  return { label, receipts, payments, net: receipts - payments }
})

const monthLabels = ['فروردین', 'اردیبهشت', 'خرداد', 'تیر', 'مرداد', 'شهریور']

export const profitLossMonthly: ProfitLossPoint[] = monthLabels.map((label) => {
  const revenue = 60_000_000 + Math.round(Math.random() * 40_000_000)
  const expense = 30_000_000 + Math.round(Math.random() * 25_000_000)
  return { label, revenue, expense, profit: revenue - expense }
})
