<script setup lang="ts">
import { formatCurrency, formatJalaliDate } from '~/utils/financeFormat'

const route = useRoute()
const id = route.params.id as string
const store = usePurchaseStore()
onMounted(() => store.fetchAll())
const purchase = computed(() => store.byId(id))

const statusLabel: Record<string, string> = { paid: 'Paid', partial: 'Partially paid', unpaid: 'Unpaid' }
const statusTone: Record<string, 'gain' | 'pending' | 'debt'> = { paid: 'gain', partial: 'pending', unpaid: 'debt' }

function printInvoice() { window.print() }
</script>

<template>
  <div v-if="!purchase" class="py-16 text-center text-sm text-ink-700/50">فاکتور یافت نشد.</div>
  <div v-else class="mx-auto max-w-2xl space-y-4">
    <div class="flex items-center justify-between">
      <h1 class="text-xl font-bold text-ink-900">Purchase invoice {{ purchase.invoiceNumber }}</h1>
      <button class="rounded-lg border border-paper-200 px-3 py-2 text-sm text-ink-800 hover:bg-paper-50" @click="printInvoice">چاپ / PDF</button>
    </div>

    <div class="rounded-xl border border-paper-200 bg-white p-5 shadow-card">
      <div class="flex items-center justify-between border-b border-paper-100 pb-4">
        <div>
          <p class="text-xs text-ink-700/50">Supplier</p>
          <p class="text-sm font-semibold text-ink-900">{{ purchase.supplierName }}</p>
        </div>
        <div class="text-left">
          <p class="text-xs text-ink-700/50">Date</p>
          <p class="num text-sm text-ink-900">{{ formatJalaliDate(purchase.date) }}</p>
        </div>
      </div>

      <table class="mt-4 w-full text-right text-sm">
        <thead>
          <tr class="text-xs text-ink-700/50"><th class="py-2 font-medium">Item</th><th class="py-2 font-medium">Quantity</th><th class="py-2 font-medium">Unit</th><th class="py-2 font-medium">Unit price</th><th class="py-2 font-medium">Total</th></tr>
        </thead>
        <tbody>
          <tr v-for="item in purchase.items" :key="item.id" class="border-t border-paper-100">
            <td class="py-2 text-ink-900">{{ item.title }}</td>
            <td class="num py-2">{{ item.quantity }}</td>
            <td class="py-2">{{ item.unit }}</td>
            <td class="num py-2">{{ formatCurrency(item.unitPrice) }}</td>
            <td class="num py-2 font-medium">{{ formatCurrency(item.quantity * item.unitPrice) }}</td>
          </tr>
        </tbody>
      </table>

      <div class="mt-4 space-y-1 border-t border-paper-100 pt-4 text-sm">
        <div class="flex justify-between text-ink-700/70"><span>تخفیف</span><span class="num">- {{ formatCurrency(purchase.discount) }}</span></div>
        <div class="flex justify-between text-ink-700/70"><span>Tax</span><span class="num">+ {{ formatCurrency(purchase.tax) }}</span></div>
        <div class="flex justify-between text-base font-bold text-ink-900"><span>Total amount</span><span class="num">{{ formatCurrency(purchase.totalAmount) }}</span></div>
        <div class="flex justify-between text-gain-700"><span>Paid</span><span class="num">{{ formatCurrency(purchase.paidAmount) }}</span></div>
        <div class="flex justify-between text-debt-600"><span>Remaining</span><span class="num">{{ formatCurrency(purchase.remaining) }}</span></div>
      </div>

      <div class="mt-4"><AppStatusBadge :label="statusLabel[purchase.status]" :tone="statusTone[purchase.status]" /></div>
      <p v-if="purchase.description" class="mt-4 text-sm text-ink-700/70">{{ purchase.description }}</p>
    </div>
  </div>
</template>
