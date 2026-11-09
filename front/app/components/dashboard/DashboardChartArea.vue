<template>
  <ChartContainer
    :config="chartConfig"
    class="h-[400px]"
  >
    <VisXYContainer
      :data="data"
      :svg-defs="svgDefs"
      :margin="{ left: 20, right: 20 }"
    >
      <VisArea
        :x="(d: T, i: number) => i"
        :y=" [(d: T) => d.amount]"
        :color="(d: T, i: number) => ['url(#fillAmount)'][i]"
        :opacity="0.4"
      />
      <VisLine
        :x="(d: T, i: number) => i"
        :y=" [(d: T) => d.amount]"
        :color="(d: T, i: number) => [chartConfig.amount.color][i]"
        :line-width="2"
      />

      <VisAxis
        type="x"
        :tick-line="false"
        :grid-line="false"
        :domain-line="true"
        :tick-values="data.map((d, i) => i)"
        :tick-format="(d: number, i: number) => {
          if (i === 0 || i === data.length - 1 || !data[i]) {
            return ''
          }
          return data[i]?.date ? formatDateByPeriod(data[i].date)[period] : ''
        }"
      />
      <VisAxis
        type="y"
        :tick-line="false"
        :grid-line="false"
        :domain-line="false"
        :tick-format="(d: number, index: number) => ''"
      />
      <ChartTooltip />
      <ChartCrosshair
        :template="componentToString(chartConfig, ChartTooltipContent, {
          labelKey: 'date',
          labelFormatter: (d) => {
            const i = d as number
            return data[i]?.date ? formatDateByPeriod(data[i].date)[period] : ''
          },
          valueFormatter: (v) => {
            return formatCurrency(v)
          },
        })"
        :color="chartConfig.amount.color"
      />
    </VisXYContainer>
  </ChartContainer>
</template>

<script lang="ts" setup generic="T extends { date: Date, amount: number }">
import { VisArea, VisAxis, VisLine, VisXYContainer } from '@unovis/vue'
import { ChartTooltipContent, componentToString, type ChartConfig } from '~/components/ui/chart'
import type { Period } from '~/types'

defineProps<{
  data: T[]
  period: Period
}>()

const chartConfig = {
  amount: {
    label: 'Amount',
    color: 'var(--primary)',
  },
} satisfies ChartConfig

const svgDefs = `
  <linearGradient id="fillAmount" x1="0" y1="0" x2="0" y2="1">
    <stop
      offset="5%"
      stop-color="var(--color-amount)"
      stop-opacity="0.8"
    />
    <stop
      offset="95%"
      stop-color="var(--color-amount)"
      stop-opacity="0.1"
    />
  </linearGradient>
`
</script>
