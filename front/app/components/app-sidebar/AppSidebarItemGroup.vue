<template>
  <Collapsible
    v-model:open="collapse"
    :default-open="isActiveRoute"
    :class="[
      'group/collapsible rounded-md',
      isHighlighted && 'text-primary-content bg-transparent from-primary/10 to-primary/5',
      props.item.title === 'مالی' && 'finance-sidebar-group',
    ]"
  >
    <CollapsibleTrigger as-child>
      <SidebarMenuButton
        class="transition-colors duration-200 dark:hover:bg-sidebar-accent/50 bg-linear-[135deg] rtl:bg-linear-[-135deg] data-[state=open]:bg-transparent data-[active=true]:text-primary-content data-[active=true]:bg-transparent data-[active=true]:from-primary/10 data-[active=true]:to-primary/5 data-[active=true]:hover:bg-transparent"
        :tooltip="item.title"
        :is-active="isHighlighted"
        @click="handleClick"
      >
        <Icon
          :name="item.icon || 'lucide:dot'"
          class="text-base size-4 shrink-0"
          aria-hidden="true"
        />
        <span>{{ item.title }}</span>
        <Icon
          name="lucide:chevron-right"
          class="text-sm size-3.5 ms-auto transition-[transform_opacity] duration-200 opacity-50 group-hover/collapsible:opacity-100 group-data-[state=open]/collapsible:rotate-90 rtl:-scale-x-100 group-data-[state=open]/collapsible:rtl:-rotate-90"
          aria-hidden="true"
        />
      </SidebarMenuButton>
    </CollapsibleTrigger>
    <CollapsibleContent class="overflow-hidden data-[state=open]:animate-collapsible-down data-[state=closed]:animate-collapsible-up finance-sidebar-content">
      <SidebarMenuSub
        :class="[
          'border-border',
          isActiveRoute && 'border-primary/10',
          props.item.title === 'مالی' && 'gap-2 py-2',
        ]"
      >
        <SidebarMenuSubItem
          v-for="(subLink, k) in item.children"
          :key="k"
        >
          <NuxtLink
            class="text-sidebar-foreground/80 hover:bg-sidebar-accent hover:text-sidebar-accent-foreground flex h-8 min-w-0 items-center gap-2 overflow-hidden rounded-md px-2 text-sm outline-hidden transition-colors [.is-active]:text-primary-content [.is-active]:bg-sidebar-accent"
            :to="subLink.link.to"
            exact-active-class="is-active"
          >
            <Icon
              v-if="subLink.icon"
              :name="subLink.icon"
              class="text-base size-4 shrink-0"
              aria-hidden="true"
            />
            <span class="truncate">{{ subLink.title }}</span>
          </NuxtLink>
        </SidebarMenuSubItem>
      </SidebarMenuSub>
    </CollapsibleContent>
  </Collapsible>
</template>

<script lang="ts" setup>
import type { SidebarItemGroup } from '@/types/sidebar'
import { useSidebar } from '@/components/ui/sidebar'

const props = defineProps<{
  item: SidebarItemGroup
}>()

const { state, open } = useSidebar()
const collapse = ref<boolean>()
const router = useRouter()
const currentRoute = computed(() => router.currentRoute.value)

const isActiveRoute = computed(() => {
  const activeRoute = props.item.activeRoute
  if (!activeRoute) return false
  const match = (route: string) => currentRoute.value.fullPath.includes(route)
  return Array.isArray(activeRoute)
    ? activeRoute.some(match)
    : match(activeRoute)
})
const isHighlighted = computed(() =>
  isActiveRoute.value && props.item.title !== 'مدیریت فروش و مشتریان',
)

function handleClick(_e: Event) {
  if (state.value === 'collapsed') {
    open.value = true
    nextTick(() => {
      collapse.value = true
    })
  }
}
</script>
