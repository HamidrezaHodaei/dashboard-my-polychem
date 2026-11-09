<template>
  <Card
    class="p-0 gap-0 grid divide-x-0 divide-y md:grid-cols-2 xl:grid-cols-4 md:divide-x xl:divide-y-0"
  >
    <div>
      <DashboardMetricCard
        title="مجموع درآمد"
        icon="lucide:dollar-sign"
        :perc="data.earnings?.perc"
        perc-text="نسبت به هفته گذشته"
        :value="data.earnings?.value"
        :value-format="{ style: 'currency', currency: 'USD', maximumFractionDigits: 0 }"
        :link="{ to: '/' }"
      />
    </div>

    <div class="max-xl:!border-x-0">
      <DashboardMetricCard
        title="مشتریان"
        icon="lucide:user-plus"
        :perc="data.customers?.perc"
        perc-text="نسبت به هفته گذشته"
        :value="data.customers?.value"
        :link="{ to: '/' }"
      />
    </div>

    <div class="md:!border-b-0">
      <DashboardMetricCard
        title="سفارش‌ها"
        icon="lucide:shopping-bag"
        :perc="data.orders?.perc"
        perc-text="نسبت به هفته گذشته"
        :value="data.orders?.value"
        :link="{ to: '/' }"
      />
    </div>

    <div>
      <DashboardMetricCard
        title="کاربران فعال"
        icon="lucide:activity"
        :perc="data.active_users?.perc"
        perc-text="نسبت به هفته گذشته"
        :value="data.active_users?.value"
        :link="{ to: '/' }"
      />
    </div>
  </Card>
</template>

<script lang="ts" setup>
interface DataRecord {
  value?: number
  perc?: number
}

const stats: Record<string, DataRecord> = {
  earnings: {
    value: 123456.789,
    perc: -20.1,
  },
  customers: {
    value: 36.894,
    perc: 180.1,
  },
  orders: {
    value: 21.751,
    perc: 19,
  },
  active_users: {
    value: 457,
    perc: 201,
  },
}

const { data, execute } = useAsyncData(async () => {
  await sleep(500)
  return stats
}, {
  immediate: false,
  default() {
    return {
      earnings: null,
      customers: null,
      orders: null,
      active_users: null,
    }
  },
})

onMounted(() => {
  execute()
})
</script>
