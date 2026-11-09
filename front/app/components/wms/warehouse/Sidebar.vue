<template>
  <aside
    class="flex h-screen shrink-0 flex-col border-r border-line bg-paper-raised transition-[width] duration-150"
    :class="settings.sidebarCollapsed ? 'w-16' : 'w-60'"
  >
    <div class="flex h-14 items-center gap-2.5 border-b border-line px-4">
      <div class="flex h-7 w-7 shrink-0 items-center justify-center rounded bg-ink text-amber-400">
        <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M3 9.5l9-6 9 6M4.5 10v9a1 1 0 001 1h4v-6h5v6h4a1 1 0 001-1v-9" />
        </svg>
      </div>
      <span v-if="!settings.sidebarCollapsed" class="truncate text-sm font-semibold tracking-tight text-ink">Warehouse Panel</span>
    </div>

    <nav class="flex-1 space-y-0.5 overflow-y-auto px-2.5 py-3">
      <NuxtLink
        v-for="item in navItems"
        :key="item.to"
        :to="item.to"
        class="focus-ring group flex items-center gap-2.5 rounded px-2.5 py-2 text-sm font-medium text-ink-soft transition-colors hover:bg-steel-50 hover:text-ink dark:hover:bg-steel-800"
        active-class="!bg-steel-100 !text-ink dark:!bg-steel-800"
      >
        <span class="shrink-0 text-ink-faint group-hover:text-ink" v-html="item.icon" />
        <span v-if="!settings.sidebarCollapsed" class="truncate">{{ item.label }}</span>
      </NuxtLink>
    </nav>

    <button
      class="focus-ring flex h-11 items-center justify-center border-t border-line text-ink-faint hover:bg-steel-50 hover:text-ink dark:hover:bg-steel-800"
      @click="settings.toggleSidebar"
    >
      <svg class="h-4 w-4 transition-transform" :class="settings.sidebarCollapsed ? 'rotate-180' : ''" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path stroke-linecap="round" stroke-linejoin="round" d="M15 19l-7-7 7-7" />
      </svg>
    </button>
  </aside>
</template>

<script setup lang="ts">
const settings = useSettingsStore()

const icon = (d: string) => `<svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path stroke-linecap="round" stroke-linejoin="round" d="${d}"/></svg>`

const navItems = [
  { label: 'Dashboard', to: '/', icon: icon('M4 4h6v6H4V4zm10 0h6v6h-6V4zM4 14h6v6H4v-6zm10 0h6v6h-6v-6z') },
  { label: 'Inventory', to: '/inventory', icon: icon('M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4') },
  { label: 'Inbound', to: '/inbound', icon: icon('M12 4v12m0 0l-4-4m4 4l4-4M4 20h16') },
  { label: 'Outbound', to: '/outbound', icon: icon('M12 20V8m0 0l-4 4m4-4l4 4M4 4h16') },
  { label: 'Stock Movements', to: '/movements', icon: icon('M8 7h12m0 0l-4-4m4 4l-4 4M16 17H4m0 0l4 4m-4-4l4-4') },
  { label: 'Transfers', to: '/transfers', icon: icon('M3 7h13l-3-3m3 3l-3 3M21 17H8l3 3m-3-3l3-3') },
  { label: 'Reports', to: '/reports', icon: icon('M9 3v18M15 8v13M4 13v8M20 3v18') },
  { label: 'Settings', to: '/settings', icon: icon('M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z M15 12a3 3 0 11-6 0 3 3 0 016 0z') }
]
</script>

