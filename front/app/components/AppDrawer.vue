<script setup lang="ts">
const props = withDefaults(defineProps<{ modelValue: boolean; title: string }>(), {})
const emit = defineEmits<{ (e: 'update:modelValue', v: boolean): void }>()
function close() { emit('update:modelValue', false) }
</script>

<template>
  <Teleport to="body">
    <div v-if="modelValue" class="fixed inset-0 z-[80] bg-ink-950/40" @click="close" />
    <Transition name="slide">
      <aside v-if="modelValue" class="fixed inset-y-0 right-0 z-[85] flex w-full max-w-sm flex-col bg-white shadow-xl">
        <div class="flex items-center justify-between border-b border-paper-200 px-5 py-4">
          <h3 class="text-base font-semibold text-ink-900">{{ title }}</h3>
          <button class="rounded-lg p-1.5 text-ink-700/60 hover:bg-paper-100" @click="close">✕</button>
        </div>
        <div class="flex-1 overflow-y-auto p-5">
          <slot />
        </div>
        <div v-if="$slots.footer" class="border-t border-paper-200 p-4">
          <slot name="footer" />
        </div>
      </aside>
    </Transition>
  </Teleport>
</template>

<style scoped>
.slide-enter-active, .slide-leave-active { transition: transform 0.2s ease; }
.slide-enter-from, .slide-leave-to { transform: translateX(100%); }
</style>
