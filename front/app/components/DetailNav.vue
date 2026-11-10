<!-- Quick-jump chips for a full-screen detail modal. Put it right BEFORE the scrolling body
     (<div class="detail-body">); it reads the body's <section><h3> titles and scrolls to them. -->
<template>
  <div
    ref="root"
    class="detail-nav"
  >
    <nav
      v-if="items.length > 1"
      class="flex gap-2 overflow-x-auto border-b bg-muted/30 px-6 py-2"
      aria-label="بخش‌های پرونده"
    >
      <button
        v-for="it in items"
        :key="it.index"
        type="button"
        class="shrink-0 rounded-full border bg-background px-3 py-1 text-xs font-medium text-muted-foreground transition-colors hover:border-primary hover:text-primary"
        @click="jump(it.index)"
      >
        {{ it.label }}
      </button>
    </nav>
  </div>
</template>

<script setup lang="ts">
const props = defineProps<{ watchKey?: string | number | null }>()
const root = ref<HTMLElement | null>(null)
const items = ref<{ index: number, label: string }[]>([])

const body = () => root.value?.nextElementSibling as HTMLElement | null
function scan() {
  const sections = Array.from(body()?.querySelectorAll(':scope > section') ?? [])
  items.value = sections
    .map((s, index) => ({ index, label: s.querySelector('h3')?.textContent?.trim() ?? '' }))
    .filter(i => i.label)
}
function jump(index: number) {
  const el = body()?.querySelectorAll(':scope > section')[index] as HTMLElement | undefined
  el?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}
onMounted(() => nextTick(scan))
watch(() => props.watchKey, () => nextTick(() => setTimeout(scan, 50)))
</script>
