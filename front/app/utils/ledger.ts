import type { Transaction, Purchase, LedgerEntry } from '~/types/finance'

/**
 * Builds a chronological debit/credit ledger for one party.
 * Convention: a receipt from the party is a credit (reduces what they owe us);
 * a payment to the party, or a purchase invoice from a supplier, is a debit.
 * This keeps the demo data internally consistent — swap for a real
 * `/api/parties/:id/ledger` endpoint once a backend exists.
 */
export function buildPartyLedger(
  partyId: string,
  transactions: Transaction[],
  purchases: Purchase[] = [],
): LedgerEntry[] {
  type RawEntry = { date: string; description: string; debit: number; credit: number }

  const raw: RawEntry[] = []

  transactions
    .filter((t) => t.partyId === partyId)
    .forEach((t) => {
      if (t.type === 'receipt') raw.push({ date: t.date, description: t.description || 'Funds received', debit: 0, credit: t.amount })
      else raw.push({ date: t.date, description: t.description || 'Funds paid', debit: t.amount, credit: 0 })
    })

  purchases
    .filter((p) => p.supplierId === partyId)
    .forEach((p) => {
      raw.push({ date: p.date, description: `Purchase invoice ${p.invoiceNumber}`, debit: p.totalAmount, credit: 0 })
      if (p.paidAmount > 0) raw.push({ date: p.date, description: `Payment for invoice ${p.invoiceNumber}`, debit: 0, credit: p.paidAmount })
    })

  raw.sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime())

  let balance = 0
  return raw.map((entry, i) => {
    balance += entry.debit - entry.credit
    return { id: `ledger-${partyId}-${i}`, ...entry, balance }
  })
}

/**
 * Builds a running-balance ledger for one financial account.
 * Convention: a receipt into the account is a debit (balance increases);
 * a payment out of the account is a credit (balance decreases).
 */
export function buildAccountLedger(
  accountId: string,
  transactions: Transaction[],
  openingBalance = 0,
): LedgerEntry[] {
  const related = transactions
    .filter((t) => t.accountId === accountId)
    .slice()
    .sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime())

  let balance = openingBalance
  return related.map((t, i) => {
    const debit = t.type === 'receipt' ? t.amount : 0
    const credit = t.type === 'payment' ? t.amount : 0
    balance += debit - credit
    return {
      id: `acc-ledger-${accountId}-${i}`,
      date: t.date,
      description: t.description || (t.type === 'receipt' ? `Receipt from ${t.partyName}` : `Payment to ${t.partyName}`),
      debit,
      credit,
      balance,
    }
  })
}
