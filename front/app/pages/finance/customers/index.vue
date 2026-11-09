<script setup lang="ts">
import { formatCurrency, formatJalaliDate } from '~/utils/financeFormat'

const store = useCustomerStore()
const { items, isLoading, error } = storeToRefs(store)
onMounted(() => store.fetchAll())

const search = ref('')
const page = ref(1)
const pageSize = 8

const filtered = computed(() => items.value.filter((c) => !search.value || c.name.includes(search.value) || c.mobile.includes(search.value)))
const paged = computed(() => filtered.value.slice((page.value - 1) * pageSize, page.value * pageSize))
watch(search, () => { page.value = 1 })
</script>

<template>
  <div class="space-y-4">
    <div>
      <h1 class="text-xl font-bold text-ink-900">Customer accounts</h1>
      <p class="mt-1 text-sm text-ink-700/60">Customer sales, payments, and outstanding balances</p>
    </div>

    <AppSearchInput v-model="search" placeholder="Search customers..." />

    <AppTableSkeleton v-if="isLoading" :cols="6" />
    <AppErrorState v-else-if="error" :message="error" @retry="store.fetchAll()" />
    <AppEmptyState v-else-if="!filtered.length" title="No customers found." />

    <template v-else>
      <div class="overflow-x-auto rounded-xl border border-paper-200 bg-white shadow-card">
        <table class="w-full min-w-[760px] text-right text-sm">
          <thead>
            <tr class="border-b border-paper-200 text-xs text-ink-700/60">
              <th class="px-4 py-3 font-medium">Customer</th>
              <th class="px-4 py-3 font-medium">مجموع فروش</th>
              <th class="px-4 py-3 font-medium">Total payments</th>
              <th class="px-4 py-3 font-medium">Outstanding balance</th>
              <th class="px-4 py-3 font-medium">Last payment</th>
              <th class="px-4 py-3 font-medium">Account status</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="c in paged" :key="c.id" class="cursor-pointer border-b border-paper-100 last:border-0 hover:bg-paper-50" @click="navigateTo(`/finance/customers/${c.id}`)">
              <td class="px-4 py-3 font-medium text-ink-900">{{ c.name }}</td>
              <td class="num px-4 py-3">{{ formatCurrency(Math.abs(c.balance) + 5_000_000) }}</td>
              <td class="num px-4 py-3 text-gain-700">{{ formatCurrency(5_000_000) }}</td>
              <td class="num px-4 py-3 font-medium" :class="c.balance > 0 ? 'text-debt-600' : 'text-gain-700'">{{ formatCurrency(Math.abs(c.balance)) }}</td>
              <td class="num px-4 py-3 text-ink-700/70">{{ c.lastTransactionAt ? formatJalaliDate(c.lastTransactionAt) : '—' }}</td>
              <td class="px-4 py-3">
                <AppStatusBadge :label="c.balance > 0 ? 'بدهکار' : 'تسویه'" :tone="c.balance > 0 ? 'debt' : 'gain'" />
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <AppPagination v-model:page="page" :page-size="pageSize" :total="filtered.length" />
    </template>
  </div>
</template>
