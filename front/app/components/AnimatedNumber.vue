<template>
  <NumberFlow
    v-bind="props"
    :value="localeValue"
  />
</template>

<script lang="ts" setup>
import NumberFlow, { type Format, type Value } from '@number-flow/vue'

interface NumberFlowProps {
  locales?: Intl.LocalesArgument
  format?: Format
  value: Value
  prefix?: string
  suffix?: string
  nonce?: string
  willChange?: boolean
};

const props = defineProps<NumberFlowProps>()
const { value } = toRefs(props)

const localeValue = ref<Value>(0)

watch(value, () => {
  localeValue.value = value.value
})

onMounted(() => {
  localeValue.value = value.value
})
</script>
