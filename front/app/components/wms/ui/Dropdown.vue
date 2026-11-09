<template>
  <div ref="root" class="relative inline-block text-left">
    <div @click="open = !open">
      <slot name="trigger" :open="open" />
    </div>
    <Transition
      enter-active-class="transition duration-100 ease-out"
      enter-from-class="opacity-0 scale-95"
      enter-to-class="opacity-100 scale-100"
      leave-active-class="transition duration-75 ease-in"
      leave-from-class="opacity-100 scale-100"
      leave-to-class="opacity-0 scale-95"
    >
      <div
        v-if="open"
        class="absolute z-30 mt-1 min-w-[180px] rounded-md border border-line bg-paper-raised py-1 shadow-panel"
        :class="align === 'right' ? 'right-0' : 'left-0'"
        @click="open = false"
      >
        <slot />
      </div>
    </Transition>
  </div>
</template>

<script setup lang="ts">
withDefaults(defineProps<{ align?: 'left' | 'right' }>(), { align: 'right' })
const open = ref(false)
const root = ref<HTMLElement | null>(null)
onClickOutside(root, () => { open.value = false })
</script>

