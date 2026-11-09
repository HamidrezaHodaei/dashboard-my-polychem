<template>
  <div class="overflow-x-auto">
    <table class="w-full border-collapse text-sm">
      <thead>
        <tr class="border-b border-line text-left">
          <th
            v-for="col in columns"
            :key="col.key"
            class="whitespace-nowrap px-4 py-2.5 text-xs font-medium uppercase tracking-wide text-ink-faint"
            :class="col.align === 'right' ? 'text-right' : col.align === 'center' ? 'text-center' : 'text-left'"
            :style="col.width ? { width: col.width } : {}"
          >
            {{ col.label }}
          </th>
          <th v-if="$slots.actions" class="w-10 px-4 py-2.5" />
        </tr>
      </thead>
      <tbody>
        <tr v-if="loading">
          <td :colspan="columns.length + ($slots.actions ? 1 : 0)">
            <WmsUiLoadingState />
          </td>
        </tr>
        <tr v-else-if="rows.length === 0">
          <td :colspan="columns.length + ($slots.actions ? 1 : 0)">
            <slot name="empty">
              <WmsUiEmptyState title="No records found" description="Try adjusting your filters or search terms." />
            </slot>
          </td>
        </tr>
        <tr
          v-for="(row, i) in rows"
          v-else
          :key="rowKey ? row[rowKey] : i"
          class="border-b border-line/70 last:border-0 hover:bg-steel-50/60 dark:hover:bg-steel-800/40"
        >
          <td
            v-for="col in columns"
            :key="col.key"
            class="whitespace-nowrap px-4 py-2.5 text-ink"
            :class="col.align === 'right' ? 'text-right' : col.align === 'center' ? 'text-center' : 'text-left'"
          >
            <slot :name="`cell-${col.key}`" :row="row">
              {{ col.formatter ? col.formatter(row) : row[col.key] }}
            </slot>
          </td>
          <td v-if="$slots.actions" class="px-4 py-2.5 text-right">
            <slot name="actions" :row="row" />
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup lang="ts">
import type { TableColumn } from '~/types'

withDefaults(defineProps<{
  columns: TableColumn[]
  rows: any[]
  loading?: boolean
  rowKey?: string
}>(), { loading: false, rowKey: 'id' })
</script>

