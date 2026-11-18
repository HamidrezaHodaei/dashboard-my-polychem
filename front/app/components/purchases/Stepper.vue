<!-- <PurchasesStepper :stages :current :finished /> : life-cycle stepper that runs RIGHT TO LEFT.
     The coloured line starts at the right-hand (first) step and grows leftwards as the request advances.
     On small screens it scrolls sideways (starting at the right) instead of squeezing the steps. -->
<template>
  <div dir="rtl" class="overflow-x-auto pb-1" role="list" aria-label="مراحل پیگیری درخواست">
    <div class="relative min-w-[600px]">
      <!-- track: from the centre of the first (right) step to the centre of the last (left) one -->
      <div class="absolute top-[15px] h-0.5 rounded bg-muted" :style="{ right: inset, left: inset }">
        <div class="absolute inset-y-0 right-0 rounded bg-primary transition-[width] duration-500" :style="{ width: `${pct}%` }" />
      </div>
      <ol class="relative flex">
        <li v-for="(s, i) in stages" :key="s.key" class="flex min-w-0 flex-1 flex-col items-center gap-1.5 text-center" role="listitem" :aria-current="i === current && !finished ? 'step' : undefined">
          <span
            class="relative z-10 flex size-8 items-center justify-center rounded-full border-2 text-xs font-semibold transition-colors"
            :class="state(i) === 'done' ? 'border-primary bg-primary text-primary-foreground' : state(i) === 'current' ? 'border-primary bg-background text-primary ring-4 ring-primary/20' : 'border-muted bg-background text-muted-foreground'"
          >
            <Icon v-if="state(i) === 'done'" name="lucide:check" class="size-4" />
            <template v-else>{{ (i + 1).toLocaleString('fa-IR') }}</template>
          </span>
          <span class="px-1 text-xs leading-tight" :class="state(i) === 'pending' ? 'text-muted-foreground' : 'font-medium'">{{ s.label }}</span>
        </li>
      </ol>
    </div>
  </div>
</template>

<script setup lang="ts">
const props = defineProps<{ stages: readonly { key: string, label: string }[], current: number, finished?: boolean }>()
const n = computed(() => props.stages.length)
const inset = computed(() => `calc(100% / ${n.value * 2})`)
const reached = computed(() => (props.finished ? n.value - 1 : Math.min(props.current, n.value - 1)))
const pct = computed(() => (n.value > 1 ? (reached.value / (n.value - 1)) * 100 : 0))
function state(i: number): 'done' | 'current' | 'pending' {
  if (props.finished || i < props.current) return 'done'
  return i === props.current ? 'current' : 'pending'
}
</script>
