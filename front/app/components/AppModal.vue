<script setup lang="ts">
const props = withDefaults(defineProps<{
  modelValue: boolean
  title: string
  size?: 'sm' | 'md' | 'lg'
}>(), { size: 'md' })

const emit = defineEmits<{ (e: 'update:modelValue', v: boolean): void }>()

const sizeClass = { sm: 'max-w-md', md: 'max-w-xl', lg: 'max-w-3xl' }
function close() { emit('update:modelValue', false) }
</script>

<template>
  <Teleport to="body">
    <Transition name="fade">
      <div v-if="modelValue" class="fixed inset-0 z-[80] flex items-center justify-center bg-ink-950/50 p-4" @click.self="close">
        <div class="max-h-[90vh] w-full overflow-y-auto rounded-2xl bg-white shadow-xl" :class="sizeClass[props.size]">
          <div class="sticky top-0 z-10 flex items-center justify-between border-b border-paper-200 bg-white px-5 py-4">
            <h3 class="text-base font-semibold text-ink-900">{{ title }}</h3>
            <button class="rounded-lg p-1.5 text-ink-700/60 hover:bg-paper-100" @click="close">✕</button>
          </div>
          <div class="p-5">
            <slot />
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.fade-enter-active, .fade-leave-active { transition: opacity 0.15s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
