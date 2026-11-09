<script setup lang="ts">
import type { LedgerEntry } from '~/types/finance'
import { formatCurrency, formatJalaliDate } from '~/utils/financeFormat'

defineProps<{ entries: LedgerEntry[] }>()
</script>

<template>
  <div class="overflow-x-auto rounded-xl border border-paper-200 bg-white shadow-card">
    <table class="w-full min-w-[560px] text-right text-sm">
      <thead>
        <tr class="border-b border-paper-200 text-xs text-ink-700/60">
          <th class="px-4 py-3 font-medium">Date</th>
          <th class="px-4 py-3 font-medium">شرح</th>
          <th class="px-4 py-3 font-medium">بدهکار</th>
          <th class="px-4 py-3 font-medium">بستانکار</th>
          <th class="px-4 py-3 font-medium">Balance</th>
        </tr>
      </thead>
      <tbody>
        <tr v-if="!entries.length">
          <td colspan="5" class="px-4 py-10 text-center text-ink-700/50">No transactions have been recorded for this account.</td>
        </tr>
        <tr v-for="e in entries" :key="e.id" class="border-b border-paper-100 last:border-0 hover:bg-paper-50">
          <td class="num px-4 py-3 text-ink-700/70">{{ formatJalaliDate(e.date) }}</td>
          <td class="px-4 py-3 text-ink-900">{{ e.description }}</td>
          <td class="num px-4 py-3 text-debt-600">{{ e.debit ? formatCurrency(e.debit) : '—' }}</td>
          <td class="num px-4 py-3 text-gain-700">{{ e.credit ? formatCurrency(e.credit) : '—' }}</td>
          <td class="num px-4 py-3 font-medium" :class="e.balance >= 0 ? 'text-debt-600' : 'text-gain-700'">
            {{ formatCurrency(Math.abs(e.balance)) }}
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
