<template>
  <ContainerWrapper class="space-y-6 py-6 md:py-8">
    <AccessPageHeader
      section="مدیریت فروش و مشتریان"
      title="داشبورد فروش"
      description="آمار و نمودارهای فروش بر اساس فیلترهای انتخابی؛ مشتریان از بانک مشتریان پنل خوانده می‌شوند."
    />

    <CrmFilterBar @apply="reload" />

    <p v-if="store.analyticsError" class="rounded-lg border border-destructive/40 p-4 text-sm text-destructive" role="alert">
      {{ store.analyticsError }}
    </p>

    <CrmKpiCards :data="store.analytics" :loading="store.analyticsLoading" />

    <template v-if="data">
      <Card v-if="!data.kpis.document_count" class="p-10 text-center text-sm text-muted-foreground shadow-none">
        با فیلترهای انتخاب‌شده فروشی پیدا نشد.
      </Card>

      <template v-else>
        <Card class="gap-4 p-5 shadow-none" :class="{ 'opacity-60': store.analyticsLoading }">
          <div class="flex flex-wrap items-center justify-between gap-2">
            <div>
              <h2 class="font-semibold">روند فروش ماهانه</h2>
              <p class="text-xs text-muted-foreground">بر اساس ماه شمسی، خالص از برگشتی‌ها · مقدار هر ماه روی ستون نوشته شده است</p>
            </div>
            <MetricToggle v-model="trendMetric" />
          </div>
          <CrmTrendChart :data="data.monthly" :metric="trendMetric" />
        </Card>

        <div class="grid gap-6 lg:grid-cols-2">
          <Card class="gap-4 p-5 shadow-none">
            <div class="flex items-center justify-between gap-2">
              <h2 class="font-semibold">سهم گریدها</h2>
              <MetricToggle v-model="productMetric" />
            </div>
            <CrmDonutChart :data="productMetric === 'amount' ? data.by_product : data.by_product_quantity" :metric="productMetric" />
          </Card>

          <Card class="gap-4 p-5 shadow-none">
            <h2 class="font-semibold">برترین مشتریان (ریال)</h2>
            <CrmRankedBars :data="data.by_customer" metric="amount" />
          </Card>

          <Card v-if="data.yearly.length > 1" class="gap-4 p-5 shadow-none">
            <h2 class="font-semibold">مقایسه سالانه (ریال)</h2>
            <CrmRankedBars :data="yearRows" metric="amount" />
          </Card>

          <Card class="gap-4 p-5 shadow-none">
            <h2 class="font-semibold">نوع فروش (ریال)</h2>
            <CrmDonutChart :data="data.by_sale_type" metric="amount" />
          </Card>

          <Card class="gap-4 p-5 shadow-none">
            <h2 class="font-semibold">نحوه پرداخت (ریال)</h2>
            <CrmDonutChart :data="data.by_payment" metric="amount" />
          </Card>

          <Card class="gap-4 p-5 shadow-none">
            <h2 class="font-semibold">فروش به تفکیک استان (کیلوگرم)</h2>
            <p class="-mt-3 text-xs text-muted-foreground">استان کارخانه در پرونده مشتری</p>
            <CrmRankedBars :data="data.by_province" metric="quantity_kg" />
          </Card>

          <Card class="gap-4 p-5 shadow-none">
            <h2 class="font-semibold">فروش به تفکیک صنعت (ریال)</h2>
            <p class="-mt-3 text-xs text-muted-foreground">صنعت فعالیت در پرونده مشتری</p>
            <CrmRankedBars :data="data.by_industry" metric="amount" />
          </Card>
        </div>
      </template>
    </template>
  </ContainerWrapper>
</template>

<script setup lang="ts">
import { defineComponent, h } from 'vue'
import type { PropType } from 'vue'
import { Button } from '~/components/ui/button'

definePageMeta({ title: 'داشبورد فروش' })

type Metric = 'amount' | 'quantity_kg'

// Small rial/kg switch used by several charts.
const MetricToggle = defineComponent({
  props: { modelValue: { type: String as PropType<Metric>, required: true } },
  emits: ['update:modelValue'],
  setup(props, { emit }) {
    return () => h('div', { class: 'flex gap-1', role: 'group' }, (['amount', 'quantity_kg'] as Metric[]).map(m =>
      h(Button, {
        size: 'sm', variant: props.modelValue === m ? 'default' : 'outline', type: 'button',
        onClick: () => emit('update:modelValue', m),
      }, () => (m === 'amount' ? 'ریال' : 'کیلوگرم'))))
  },
})

const store = useCrmStore()
const access = useCrmAccess()
const trendMetric = ref<Metric>('amount')
const productMetric = ref<Metric>('amount')

const data = computed(() => store.analytics)
const yearRows = computed(() => (data.value?.yearly ?? []).map(y => ({
  id: y.year, name: String(y.year), amount: y.amount, quantity_kg: y.quantity_kg,
})))

function reload() {
  return store.loadAnalytics()
}

onMounted(async () => {
  if (!access.canReadSales.value) return
  await Promise.all([store.loadOptions(), store.loadCatalog()])
  await reload()
})
</script>
