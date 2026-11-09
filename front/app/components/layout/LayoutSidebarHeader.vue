<template>
  <div class="relative flex h-(--header-height) items-center justify-center -my-2">
    <Button
      class="absolute end-0 group-data-[state=collapsed]:hidden group-data-[state=expanded]:hidden"
      variant="ghost"
      size="icon"
      @click="toggleSidebar"
    >
      <span class="sr-only">بستن نوار کناری</span>
      <Icon
        name="lucide:arrow-left"
        class="text-xl size-5"
        aria-hidden="true"
      />
    </Button>
    <div
      class="flex w-full justify-center"
    >
      <NuxtLink
        to="/"
        class="inline-flex w-full items-center justify-center overflow-hidden focus:outline-none focus-visible:ring-2 focus-visible:ring-ring/50"
      >
        <LogoSVG class="shrink-0" />
      </NuxtLink>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useSidebar } from '@/components/ui/sidebar'

const { toggleSidebar } = useSidebar()
</script>
