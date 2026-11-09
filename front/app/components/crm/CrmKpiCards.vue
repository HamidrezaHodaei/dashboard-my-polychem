<!-- KPI cards for the CURRENT filters (same /crm/analytics response as the charts). -->
<template>
  <div class="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
    <template v-if="loading && !data">
      <Skeleton v-for="n in 8" :key="n" class="h-[104px] rounded-xl" />
    </template>
    <template v-else-if="data">
      <Card
        v-for="c in cards"
        :key="c.label"
        class="gap-1 p-5 shadow-none"
        :class="c.featured ? 'border-primary/50 bg-primary/5' : ''"
      >
        <div class="flex items-center justify-between text-sm text-muted-foreground">
          <span>{{ c.label }}</span>
          <Icon :name="c.icon" class="size-4 text-primary" />
        </div>
        <p
          class="truncate text-xl font-semibold"
          :class="c.negative ? 'text-destructive' : ''"
          :title="c.value"
          dir="auto"
        >
          {{ c.value }}
        </p>
        <p v-if="c.note" class="truncate text-xs text-muted-foreground" dir="auto">{{ c.note }}</p>
      </Card>
    </template>
  </div>
</template>

<script setup lang="ts">
import { faNum, formatKg, formatRialCompact } from '~/utils/crm'
import type { CrmAnalytics } from '~/stores/crm'

const props = defineProps<{ data: CrmAnalytics | null, loading?: boolean }>()

const cards = computed(() => {
  const k = props.data!.kpis
  return [
    { label: 'مجموع فروش خالص', icon: 'lucide:coins', value: formatRialCompact(k.net_amount), note: 'پس از کسر برگشتی‌ها', featured: true, negative: k.net_amount < 0 },
    { label: 'مجموع مقدار خالص', icon: 'lucide:package', value: formatKg(k.net_quantity_kg), note: 'پس از کسر برگشتی‌ها', featured: true, negative: k.net_quantity_kg < 0 },
    { label: 'تعداد مشتریان', icon: 'lucide:users', value: faNum(k.customer_count), note: 'مشتری فعال در بازه انتخابی' },
    { label: 'میانگین فاکتور', icon: 'lucide:receipt', value: formatRialCompact(k.avg_invoice), note: 'به‌ازای هر فاکتور فروش' },
    { label: 'فاکتور برگشتی', icon: 'lucide:undo-2', value: faNum(k.return_count), note: 'در بازه انتخابی' },
    { label: 'بهترین مشتری', icon: 'lucide:star', value: k.top_customer?.name || '—', note: k.top_customer ? formatRialCompact(k.top_customer.amount) : '' },
    { label: 'پرفروش‌ترین گرید', icon: 'lucide:medal', value: k.top_product?.name || '—', note: k.top_product ? formatKg(k.top_product.quantity_kg) : '' },
    { label: 'تعداد فاکتور فروش', icon: 'lucide:file-text', value: faNum(k.invoice_count), note: 'فاکتور در بازه انتخابی' },
  ]
})
</script>
