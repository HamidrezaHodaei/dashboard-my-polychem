<template>
  <button
    :type="type"
    :disabled="disabled"
    class="login-btn"
    translate="no"
  >
    <span class="login-btn__label"><slot /></span>
    <Icon
      v-if="loading"
      name="lucide:loader-circle"
      class="size-5 animate-spin"
      aria-hidden="true"
    />
  </button>
</template>

<script lang="ts" setup>
withDefaults(
  defineProps<{
    type?: 'button' | 'submit' | 'reset'
    disabled?: boolean
    loading?: boolean
  }>(),
  {
    type: 'submit',
    disabled: false,
    loading: false,
  },
)
</script>

<style scoped>
.login-btn {
  --brand: #fdd00a;
  position: relative;
  isolation: isolate;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  width: 100%;
  height: 3.5rem;
  border: 2px solid var(--brand);
  border-radius: 1rem;
  background: transparent;
  font-size: 1.125rem;
  font-weight: 700;
  cursor: pointer;
  transition: color 1s ease;
}

.login-btn::before {
  content: '';
  position: absolute;
  z-index: -1;
  top: 0;
  bottom: 0;
  inset-inline-start: -40px;
  width: 0;
  transform: skewX(45deg);
  background-color: var(--brand);
  transition: width 1s ease;
}

.login-btn:hover:not(:disabled),
.login-btn:focus-visible:not(:disabled) {
  color: #fff;
}

.login-btn:hover:not(:disabled)::before,
.login-btn:focus-visible:not(:disabled)::before {
  width: 160%;
}

.login-btn:disabled {
  cursor: not-allowed;
  opacity: 0.7;
}
</style>