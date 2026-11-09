<template>
  <SidebarProvider
    :class="[
      'relative md:[&:has([data-variant=inset])_main>header]:rounded-t-xl [--header-height:66px]',
      container === 'centered' ? 'container-centered' : 'container-fluid',
      (color === 'accent' && variant === 'inset') && '[--sidebar:color-mix(in_oklab,var(--accent)_60%,var(--background))]',
    ]"
    :default-open="defaultOpen"
  >
    <LayoutSidebar
      :color="color"
      :variant="variant"
    />
    <SidebarInset
      :class="[
        'flex min-h-0 min-w-0 flex-col bg-background text-foreground',
        color !== 'accent' && 'md:peer-data-[variant=inset]:border',
      ]"
    >
      <Header />
      <div :class="[
        'min-h-0 flex-1',
        isMailRoute ? 'overflow-hidden' : 'grow',
        isFinanceRoute ? 'overflow-y-auto px-4 py-6 sm:px-6 lg:px-8' : 'overflow-hidden',
      ]">
        <div :class="[
          isFinanceRoute ? 'finance-content mx-auto w-full max-w-screen-2xl' : '',
          isMailRoute && 'h-full min-h-0',
        ]">
          <slot />
        </div>
      </div>
      <Footer v-if="!isMailRoute" />
    </SidebarInset>
  </SidebarProvider>
</template>

<script lang="ts" setup>
import type { SidebarProps } from '@/types/sidebar'
import { SIDEBAR_COOKIE_NAME } from '~/components/ui/sidebar/utils'

const defaultOpen = useCookie<boolean>(SIDEBAR_COOKIE_NAME)

const color = ref<SidebarProps['color']>('background')
const variant = ref<SidebarProps['variant']>('sidebar')
const container = ref<'fluid' | 'centered'>('fluid')
const route = useRoute()
const isFinanceRoute = computed(() => route.path === '/finance' || route.path.startsWith('/finance/'))
const isMailRoute = computed(() => route.path === '/mail' || route.path.startsWith('/mail/'))
</script>
