<script setup lang="ts">
import type { Transaction } from '~/types/finance'
import { formatCurrency, formatJalaliDate } from '~/utils/financeFormat'

defineProps<{ transactions: Transaction[] }>()

const methodLabel: Record<Transaction['method'], string> = {
  cash: 'نقدی', card: 'کارت', remittance: 'حواله', bank_transfer: 'انتقال بانکی', cheque: 'چک',
}
const statusStyle: Record<Transaction['status'], string> = {
  confirmed: 'bg-gain-50 text-gain-700',
  pending: 'bg-pending-50 text-pending-600',
  canceled: 'bg-debt-50 text-debt-600',
}
const statusLabel: Record<Transaction['status'], string> = {
  confirmed: 'تأییدشده', pending: 'در انتظار', canceled: 'لغوشده',
}
</script>

<template>
  <div class="overflow-x-auto rounded-xl border border-paper-200 bg-white shadow-card">
    <table class="w-full min-w-[720px] text-right text-sm">
      <thead>
        <tr class="border-b border-paper-200 text-xs text-ink-700/60">
          <th class="px-4 py-3 font-medium">تاریخ</th>
          <th class="px-4 py-3 font-medium">نوع</th>
          <th class="px-4 py-3 font-medium">طرف‌حساب</th>
          <th class="px-4 py-3 font-medium">مبلغ</th>
          <th class="px-4 py-3 font-medium">روش پرداخت</th>
          <th class="px-4 py-3 font-medium">وضعیت</th>
        </tr>
      </thead>
      <tbody>
        <tr v-if="!transactions.length">
          <td colspan="6" class="px-4 py-10 text-center text-ink-700/50">هنوز تراکنشی ثبت نشده است.</td>
        </tr>
        <tr v-for="t in transactions" :key="t.id" class="border-b border-paper-100 last:border-0 hover:bg-paper-50">
          <td class="num px-4 py-3 text-ink-700/70">{{ formatJalaliDate(t.date) }}</td>
          <td class="px-4 py-3">
            <span class="inline-flex items-center gap-1.5 text-xs font-medium" :class="t.type === 'receipt' ? 'text-gain-700' : 'text-debt-600'">
              <svg class="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                <path v-if="t.type === 'receipt'" d="M12 19V5M5 12l7-7 7 7" stroke-linecap="round" stroke-linejoin="round" />
                <path v-else d="M12 5v14M5 12l7 7 7-7" stroke-linecap="round" stroke-linejoin="round" />
              </svg>
              {{ t.type === 'receipt' ? 'دریافت' : 'پرداخت' }}
            </span>
          </td>
          <td class="px-4 py-3 text-ink-900">{{ t.partyName }}</td>
          <td class="num px-4 py-3 font-medium text-ink-900">{{ formatCurrency(t.amount) }}</td>
          <td class="px-4 py-3 text-ink-700/70">{{ methodLabel[t.method] }}</td>
          <td class="px-4 py-3">
            <span class="rounded-full px-2.5 py-1 text-xs font-medium" :class="statusStyle[t.status]">
              {{ statusLabel[t.status] }}
            </span>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
