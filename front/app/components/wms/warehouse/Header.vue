<template>
  <header class="flex h-14 shrink-0 items-center justify-between gap-4 border-b border-line bg-paper-raised px-5">
    <WmsWarehouseBreadcrumbs :crumbs="crumbs" />

    <div class="flex flex-1 items-center justify-end gap-3">
      <div class="relative hidden w-64 md:block">
        <svg class="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-ink-faint" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="11" cy="11" r="7" /><path stroke-linecap="round" d="M21 21l-4.3-4.3" />
        </svg>
        <input
          type="text"
          placeholder="Search items, receipts, transfersâ€¦"
          class="focus-ring h-8 w-full rounded border border-line bg-paper pl-8 pr-3 text-sm text-ink placeholder:text-ink-faint"
        />
      </div>

      <button class="focus-ring rounded p-1.5 text-ink-faint hover:bg-steel-100 hover:text-ink dark:hover:bg-steel-800" @click="settings.toggleTheme" aria-label="Toggle theme">
        <svg v-if="settings.theme === 'light'" class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
          <path stroke-linecap="round" stroke-linejoin="round" d="M21 12.79A9 9 0 1111.21 3 7 7 0 0021 12.79z" />
        </svg>
        <svg v-else class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
          <circle cx="12" cy="12" r="4" /><path stroke-linecap="round" d="M12 2v2m0 16v2M4.2 4.2l1.4 1.4m12.8 12.8l1.4 1.4M2 12h2m16 0h2M4.2 19.8l1.4-1.4M18.4 5.6l1.4-1.4" />
        </svg>
      </button>

      <button class="focus-ring relative rounded p-1.5 text-ink-faint hover:bg-steel-100 hover:text-ink dark:hover:bg-steel-800" aria-label="Notifications">
        <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
          <path stroke-linecap="round" stroke-linejoin="round" d="M15 17h5l-1.4-1.4A2 2 0 0118 14.2V11a6 6 0 10-12 0v3.2a2 2 0 01-.6 1.4L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
        </svg>
        <span class="absolute right-1.5 top-1.5 h-1.5 w-1.5 rounded-full bg-amber-500" />
      </button>

      <WmsUiDropdown>
        <template #trigger>
          <button class="focus-ring flex items-center gap-2 rounded pl-1 pr-2 py-1 hover:bg-steel-100 dark:hover:bg-steel-800">
            <span class="flex h-7 w-7 items-center justify-center rounded-full bg-steel-700 text-xs font-medium text-white">FV</span>
            <span class="hidden text-sm font-medium text-ink sm:inline">Femke Visser</span>
          </button>
        </template>
        <WmsUiDropdownItem>Profile settings</WmsUiDropdownItem>
        <WmsUiDropdownItem>Preferences</WmsUiDropdownItem>
        <WmsUiDropdownItem danger>Sign out</WmsUiDropdownItem>
      </WmsUiDropdown>
    </div>
  </header>
</template>

<script setup lang="ts">
const settings = useSettingsStore()
const props = defineProps<{ crumbs: { label: string; to?: string }[] }>()
</script>

