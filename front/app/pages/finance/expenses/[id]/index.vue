<script setup lang="ts">
import { formatCurrency, formatJalaliDate } from '~/utils/financeFormat'

const route = useRoute()
const id = route.params.id as string
const store = useExpenseStore()
const notify = useNotify()
const { confirm } = useConfirm()
onMounted(() => store.fetchAll())
const expense = computed(() => store.byId(id))
const isEditing = ref(false)

const categoryLabel: Record<string, string> = {
  salary: 'حقوق', rent: 'اجاره', transport: 'حمل و نقل', electricity: 'برق', water: 'آب', gas: 'گاز',
  internet: 'Internet', ads: 'Advertising', repairs: 'Repairs', equipment: 'Equipment', other: 'Other',
}

async function handleUpdate(payload: any) {
  await store.update(id, payload)
  isEditing.value = false
  notify.success('Expense updated.')
}
async function handleDelete() {
  const ok = await confirm('Delete this expense?')
  if (!ok) return
  await store.remove(id)
  notify.success('Expense deleted.')
  navigateTo('/finance/purchases')
}
</script>

<template>
  <div v-if="!expense" class="py-16 text-center text-sm text-ink-700/50">Expense not found.</div>
  <div v-else class="mx-auto max-w-2xl space-y-4">
    <div class="flex items-center justify-between">
      <h1 class="text-xl font-bold text-ink-900">{{ expense.title }}</h1>
      <div class="flex gap-2">
        <button v-if="!isEditing" class="rounded-lg border border-paper-200 px-3 py-2 text-sm text-ink-800 hover:bg-paper-50" @click="isEditing = true">Edit</button>
        <button class="rounded-lg border border-debt-600/30 px-3 py-2 text-sm text-debt-600 hover:bg-debt-50" @click="handleDelete">Delete</button>
      </div>
    </div>
    <div v-if="!isEditing" class="grid grid-cols-1 gap-4 rounded-xl border border-paper-200 bg-white p-5 shadow-card sm:grid-cols-2">
      <div><p class="text-xs text-ink-700/50">دسته‌بندی</p><p class="mt-1 text-sm text-ink-900">{{ categoryLabel[expense.category] }}</p></div>
      <div><p class="text-xs text-ink-700/50">Amount</p><p class="num mt-1 text-sm font-semibold text-debt-600">{{ formatCurrency(expense.amount) }}</p></div>
      <div><p class="text-xs text-ink-700/50">Date</p><p class="num mt-1 text-sm text-ink-900">{{ formatJalaliDate(expense.date) }}</p></div>
      <div><p class="text-xs text-ink-700/50">Payment method</p><p class="mt-1 text-sm text-ink-900">{{ expense.method }}</p></div>
      <div v-if="expense.description" class="sm:col-span-2"><p class="text-xs text-ink-700/50">Description</p><p class="mt-1 text-sm text-ink-900">{{ expense.description }}</p></div>
    </div>
    <div v-else class="rounded-xl border border-paper-200 bg-white p-5 shadow-card">
      <ExpenseForm :initial="expense" @submit="handleUpdate" @cancel="isEditing = false" />
    </div>
  </div>
</template>
