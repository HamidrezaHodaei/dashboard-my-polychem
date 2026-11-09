<template>
  <div v-if="status === 'pending' && !data.length">
    <DashboardChartSkeleton />
  </div>
  <DashboardChartCard
    v-else
    class="relative overflow-hidden"
  >
    <template #header>
      <div>
        <p class="mb-1 text-sm font-medium text-muted-foreground">
          Revenue
        </p>
        <p class="text-3xl font-semibold">
          <AnimatedNumber
            :value="total"
            :format="{ style: 'currency', currency: 'USD', maximumFractionDigits: 0 }"
          />
        </p>
      </div>
    </template>
    <ProgressIndeterminate
      v-if="status === 'pending'"
      class="absolute top-0 inset-0"
    />
    <DashboardChartArea
      :data="data"
      :period="period"
    />
  </DashboardChartCard>
</template>

<script lang="ts" setup>
import type { DateRange } from 'reka-ui'
import {
  eachDayOfInterval,
  eachWeekOfInterval,
  eachMonthOfInterval,
} from 'date-fns'
import { getLocalTimeZone } from '@internationalized/date'
import type { Period } from '~/types'

interface DataRecord {
  date: Date
  amount: number
}

const props = defineProps<{
  period: Period
  range: DateRange
}>()

const startDateRange = computed(() => {
  if (!props.range.start) return null
  return props.range.start.toDate(getLocalTimeZone())
})

const endDateRange = computed(() => {
  if (!props.range.end) return null
  return props.range.end.toDate(getLocalTimeZone())
})

const { data, status, execute } = await useAsyncData<DataRecord[]>(
  async () => {
    await sleep(1000)
    return generateRandomData(startDateRange.value, endDateRange.value, props.period)
  },
  {
    default: () => [],
    immediate: false,
  },
)

const total = computed(() =>
  data.value.reduce((acc: number, { amount }) => acc + amount, 0),
)

const generateRandomData = (start: Date | null, end: Date | null, period: Period): DataRecord[] => {
  if (!start || !end) return []
  let dates: Date[] = []
  if (period === 'daily') {
    dates = eachDayOfInterval({ start, end })
  }
  else if (period === 'weekly') {
    dates = eachWeekOfInterval({ start, end })
  }
  else if (period === 'monthly') {
    dates = eachMonthOfInterval({ start, end })
  }

  return dates.map(date => ({
    date,
    amount: Math.floor(Math.random() * 2000) + 500,
  }))
}

watch([() => props.period, () => props.range], () => {
  execute()
}, { immediate: true })
</script>
