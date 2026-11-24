<template>
  <DropdownMenu v-if="visible.length">
    <DropdownMenuTrigger as-child>
      <Button
        variant="ghost"
        size="icon-sm"
        class="text-muted-foreground data-[state=open]:bg-accent data-[state=open]:text-foreground"
        :aria-label="label"
        :title="label"
        @click.stop
      >
        <Icon
          name="lucide:ellipsis-vertical"
          class="size-4"
          aria-hidden="true"
        />
      </Button>
    </DropdownMenuTrigger>

    <!-- Text-only items: the label is the whole affordance (no per-item icons). RTL, kept inside the
         viewport by collision padding so it never spills off a phone screen. -->
    <DropdownMenuContent
      :align="align"
      dir="rtl"
      :collision-padding="12"
      class="min-w-44"
      @click.stop
    >
      <template
        v-for="(item, i) in visible"
        :key="item.key"
      >
        <DropdownMenuSeparator v-if="i > 0 && separatorBefore(i)" />

        <DropdownMenuItem
          v-if="item.to && !item.disabled"
          as-child
          :variant="item.destructive ? 'destructive' : 'default'"
        >
          <NuxtLink :to="item.to">
            {{ item.label }}
          </NuxtLink>
        </DropdownMenuItem>

        <DropdownMenuItem
          v-else
          :disabled="item.disabled"
          :variant="item.destructive ? 'destructive' : 'default'"
          @select="item.onSelect?.()"
        >
          {{ item.label }}
        </DropdownMenuItem>
      </template>
    </DropdownMenuContent>
  </DropdownMenu>
</template>

<script lang="ts" setup>
import type { RowAction } from '@/types/row-actions'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'

/**
 * The single "row actions" pattern of the panel: one vertical-ellipsis button that opens a menu of
 * everything the user can do with that record. Pass every possible action and set `show` from the
 * permission / status rules; hidden actions are dropped, and with none left nothing is rendered.
 * Ordering: items keep the given order, but destructive items always go last, behind a separator.
 */
const props = withDefaults(defineProps<{
  actions: RowAction[]
  label?: string
  align?: 'start' | 'center' | 'end'
}>(), {
  label: 'عملیات',
  align: 'start',
})

const visible = computed(() => {
  const shown = props.actions.filter(a => a.show !== false)
  return [...shown.filter(a => !a.destructive), ...shown.filter(a => a.destructive)]
})

const groupOf = (a: RowAction) => (a.destructive ? Number.MAX_SAFE_INTEGER : (a.group ?? 0))
const separatorBefore = (i: number) => groupOf(visible.value[i]!) !== groupOf(visible.value[i - 1]!)
</script>
