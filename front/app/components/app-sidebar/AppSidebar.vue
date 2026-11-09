<template>
  <Sidebar
    collapsible="icon"
    :side="side"
    :variant="variant"
    :portal="{ to: `#app-sidebar-${id}` }"
    :class="[color === 'dark' && 'dark text-sidebar-foreground']"
  >
    <SidebarHeader v-if="$slots.header">
      <slot name="header" />
    </SidebarHeader>

    <SidebarContent class="[scrollbar-width:thin]">
      <AppSidebarNavGroup
        v-for="(group, i) in nav"
        :key="`main-${i}`"
        :group="group"
      />

      <template v-if="secondaryNav?.length">
        <div class="mt-auto" />
        <AppSidebarNavGroup
          v-for="(group, i) in secondaryNav"
          :key="`secondary-${i}`"
          :group="group"
        />
      </template>
    </SidebarContent>

    <SidebarFooter v-if="$slots.footer">
      <slot name="footer" />
    </SidebarFooter>
  </Sidebar>

  <Teleport to="body">
    <div
      :id="`app-sidebar-${id}`"
      :class="color === 'dark' && 'dark'"
    />
  </Teleport>

  <!-- Background for sidebar wrapper inset variant -->
  <div
    v-if="variant === 'inset'"
    :class="color === 'dark' && 'dark'"
  >
    <div class="bg-(--sidebar) absolute inset-0" />
  </div>
</template>

<script setup lang="ts">
import type { SidebarProps } from '@/types/sidebar'

withDefaults(defineProps<SidebarProps>(), {
  color: 'background',
  side: 'right',
  variant: 'sidebar',
})

const id = useId()
</script>
