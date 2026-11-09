<template>
  <div class="grid grid-cols-1 gap-6 xl:grid-cols-3">
    <DashboardCard
      title="Pending approvals"
      description="Items waiting for your review"
      icon="lucide:inbox"
    >
      <div class="space-y-1">
        <NuxtLink
          v-for="approval in approvals"
          :key="approval.title"
          :to="approval.to"
          class="flex items-center gap-3 rounded-md px-2 py-3 transition-colors hover:bg-muted/70 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          <span
            class="flex size-8 shrink-0 items-center justify-center rounded-md bg-warning/10 text-warning"
          >
            <Icon
              :name="approval.icon"
              class="size-4"
              aria-hidden="true"
            />
          </span>
          <span class="min-w-0 flex-1">
            <span class="block truncate text-sm font-medium">{{ approval.title }}</span>
            <span class="block truncate text-xs text-muted-foreground">{{ approval.meta }}</span>
          </span>
          <Icon
            name="lucide:chevron-right"
            class="size-4 text-muted-foreground"
            aria-hidden="true"
          />
        </NuxtLink>
      </div>
    </DashboardCard>

    <DashboardCard
      title="Operational alerts"
      description="Needs attention today"
      icon="lucide:triangle-alert"
    >
      <div class="space-y-1">
        <NuxtLink
          v-for="alert in alerts"
          :key="alert.title"
          :to="alert.to"
          class="flex items-center gap-3 rounded-md px-2 py-3 transition-colors hover:bg-muted/70 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          <span
            class="flex size-8 shrink-0 items-center justify-center rounded-md"
            :class="alert.tone === 'danger' ? 'bg-destructive/10 text-destructive' : 'bg-info/10 text-info'"
          >
            <Icon
              :name="alert.icon"
              class="size-4"
              aria-hidden="true"
            />
          </span>
          <span class="min-w-0 flex-1">
            <span class="block truncate text-sm font-medium">{{ alert.title }}</span>
            <span class="block truncate text-xs text-muted-foreground">{{ alert.meta }}</span>
          </span>
          <span class="text-xs font-medium text-muted-foreground">{{ alert.count }}</span>
        </NuxtLink>
      </div>
    </DashboardCard>

    <DashboardCard
      title="My tasks"
      description="Your work for today"
      icon="lucide:check-check"
    >
      <div class="space-y-4">
        <div class="flex items-end justify-between gap-3">
          <div>
            <p class="text-2xl font-bold">8 <span class="text-sm font-normal text-muted-foreground">of 12 done</span></p>
            <p class="text-xs text-muted-foreground">67% completed this week</p>
          </div>
          <NuxtLink
            to="/tasks/my-tasks"
            class="text-sm font-medium text-primary hover:underline"
          >
            View all
          </NuxtLink>
        </div>
        <div class="h-2 overflow-hidden rounded-full bg-muted">
          <div class="h-full w-2/3 rounded-full bg-primary" />
        </div>
        <div class="flex items-center justify-between border-t border-border pt-3 text-sm">
          <span class="text-muted-foreground">Next deadline</span>
          <span class="font-medium">Today, 4:30 PM</span>
        </div>
      </div>
    </DashboardCard>
  </div>
</template>

<script lang="ts" setup>
const approvals = [
  {
    title: 'Purchase order #PO-1048',
    meta: 'Procurement · 2 hours ago',
    icon: 'lucide:receipt-text',
    to: '/finance/purchases',
  },
  {
    title: 'Payment batch #PAY-238',
    meta: 'Finance · 4 hours ago',
    icon: 'lucide:banknote',
    to: '/finance/payments',
  },
  {
    title: 'New website page',
    meta: 'Website · Yesterday',
    icon: 'lucide:file-check-2',
    to: '/website/blog',
  },
]

const alerts = [
  {
    title: 'Low inventory',
    meta: 'Polymer additive P-240',
    icon: 'lucide:package-open',
    count: '4 items',
    tone: 'danger',
    to: '/inventory/stock',
  },
  {
    title: 'Overdue receivables',
    meta: 'Invoices past due date',
    icon: 'lucide:clock-3',
    count: '7 invoices',
    tone: 'danger',
    to: '/finance/overdue',
  },
  {
    title: 'Production update',
    meta: 'Schedule requires review',
    icon: 'lucide:factory',
    count: '2 plans',
    tone: 'info',
    to: '/tasks/team',
  },
]
</script>
