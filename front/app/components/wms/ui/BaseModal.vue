<template>
  <Teleport to="body">
    <Transition
      enter-active-class="transition duration-150 ease-out"
      enter-from-class="opacity-0"
      enter-to-class="opacity-100"
      leave-active-class="transition duration-100 ease-in"
      leave-from-class="opacity-100"
      leave-to-class="opacity-0"
    >
      <div v-if="modelValue" class="fixed inset-0 z-40 flex items-center justify-center p-4">
        <div class="absolute inset-0 bg-ink/40 backdrop-blur-[2px]" @click="close" />
        <Transition
          enter-active-class="transition duration-150 ease-out"
          enter-from-class="opacity-0 translate-y-2 scale-[0.98]"
          enter-to-class="opacity-100 translate-y-0 scale-100"
        >
          <div
            v-if="modelValue"
            role="dialog"
            aria-modal="true"
            :aria-label="title"
            class="relative z-10 flex max-h-[88vh] w-full flex-col rounded-lg border border-line bg-paper-raised shadow-panel"
            :class="sizeClass"
          >
            <div class="flex items-center justify-between border-b border-line px-5 py-4">
              <div>
                <h2 class="text-sm font-semibold text-ink">{{ title }}</h2>
                <p v-if="subtitle" class="mt-0.5 text-xs text-ink-faint">{{ subtitle }}</p>
              </div>
              <button class="focus-ring rounded p-1 text-ink-faint hover:bg-steel-100 hover:text-ink dark:hover:bg-steel-800" @click="close">
                <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path stroke-linecap="round" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            <div class="overflow-y-auto px-5 py-4">
              <slot />
            </div>
            <div v-if="$slots.footer" class="flex items-center justify-end gap-2 border-t border-line px-5 py-3.5">
              <slot name="footer" />
            </div>
          </div>
        </Transition>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
const props = withDefaults(defineProps<{
  modelValue: boolean
  title: string
  subtitle?: string
  size?: 'sm' | 'md' | 'lg'
}>(), { size: 'md' })

const emit = defineEmits(['update:modelValue'])

function close() {
  emit('update:modelValue', false)
}

const sizeClass = computed(() => ({
  sm: 'max-w-md',
  md: 'max-w-xl',
  lg: 'max-w-3xl'
}[props.size]))

// Escape key closes the dialog
function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Escape' && props.modelValue) close()
}
onMounted(() => window.addEventListener('keydown', onKeydown))
onUnmounted(() => window.removeEventListener('keydown', onKeydown))
</script>

