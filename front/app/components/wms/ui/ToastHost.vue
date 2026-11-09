<template>
  <Teleport to="body">
    <div class="pointer-events-none fixed bottom-4 right-4 z-50 flex w-80 flex-col gap-2">
      <TransitionGroup
        enter-active-class="transition duration-200 ease-out"
        enter-from-class="opacity-0 translate-y-1"
        leave-active-class="transition duration-150 ease-in"
        leave-to-class="opacity-0"
      >
        <div
          v-for="t in toastStore.items"
          :key="t.id"
          class="pointer-events-auto flex items-start gap-2.5 rounded-md border border-line bg-paper-raised px-3.5 py-3 shadow-panel"
        >
          <span class="mt-0.5 h-2 w-2 shrink-0 rounded-full" :class="dotClass(t.tone)" />
          <div class="min-w-0 flex-1">
            <p class="text-sm font-medium text-ink">{{ t.title }}</p>
            <p v-if="t.description" class="mt-0.5 text-xs text-ink-faint">{{ t.description }}</p>
          </div>
          <button class="text-ink-faint hover:text-ink" @click="toastStore.dismiss(t.id)">
            <svg class="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      </TransitionGroup>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
const toastStore = useToastStore()
function dotClass(tone: string) {
  return { success: 'bg-success', danger: 'bg-danger', info: 'bg-info' }[tone] ?? 'bg-steel-400'
}
</script>

