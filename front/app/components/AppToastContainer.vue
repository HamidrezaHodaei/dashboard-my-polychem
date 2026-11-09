<script setup lang="ts">
const { toasts, dismiss } = useToast()

const styles = {
  success: { bg: 'bg-gain-600', icon: 'M5 13l4 4L19 7' },
  error: { bg: 'bg-debt-600', icon: 'M6 18L18 6M6 6l12 12' },
  info: { bg: 'bg-ink-800', icon: 'M12 8h.01M11 12h1v4h1' },
}
</script>

<template>
  <div class="pointer-events-none fixed bottom-4 left-4 z-[100] flex w-full max-w-xs flex-col gap-2">
    <TransitionGroup name="toast">
      <div
        v-for="t in toasts"
        :key="t.id"
        class="pointer-events-auto flex items-start gap-2.5 rounded-xl px-4 py-3 text-sm text-white shadow-lg"
        :class="styles[t.type].bg"
      >
        <svg class="mt-0.5 h-4 w-4 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path :d="styles[t.type].icon" />
        </svg>
        <p class="flex-1">{{ t.message }}</p>
        <button class="text-white/70 hover:text-white" @click="dismiss(t.id)">✕</button>
      </div>
    </TransitionGroup>
  </div>
</template>

<style scoped>
.toast-enter-active, .toast-leave-active { transition: all 0.2s ease; }
.toast-enter-from { opacity: 0; transform: translateY(8px); }
.toast-leave-to { opacity: 0; transform: translateX(-8px); }
</style>
