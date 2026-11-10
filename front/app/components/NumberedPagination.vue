<!-- <NumberedPagination :page :page-size :total :loading @update:page /> -->
<!-- Footer of a list: «قبلی / بعدی» plus numbered pages (1 … 4 5 6 … 20) and a jump-to-page box. -->
<template>
  <div
    v-if="total > pageSize"
    class="flex flex-col gap-3 border-t p-4 text-sm text-muted-foreground sm:flex-row sm:items-center sm:justify-between"
    dir="rtl"
  >
    <span>صفحه {{ fa(page) }} از {{ fa(pageCount) }} &middot; مجموع {{ fa(total) }} مورد</span>

    <nav
      class="flex flex-wrap items-center gap-1"
      aria-label="صفحه‌بندی"
    >
      <Button
        variant="outline"
        size="sm"
        :disabled="page <= 1 || loading"
        @click="go(page - 1)"
      >
        قبلی
      </Button>

      <template
        v-for="(item, i) in items"
        :key="`${item}-${i}`"
      >
        <span
          v-if="item === '…'"
          class="px-1.5"
          aria-hidden="true"
        >…</span>
        <Button
          v-else
          size="sm"
          class="min-w-8 px-2"
          :variant="item === page ? 'default' : 'outline'"
          :disabled="loading"
          :aria-current="item === page ? 'page' : undefined"
          :aria-label="`صفحه ${fa(item as number)}`"
          @click="go(item as number)"
        >
          {{ fa(item as number) }}
        </Button>
      </template>

      <Button
        variant="outline"
        size="sm"
        :disabled="page >= pageCount || loading"
        @click="go(page + 1)"
      >
        بعدی
      </Button>

      <form
        class="flex items-center gap-1 ps-2"
        @submit.prevent="jump"
      >
        <label
          class="sr-only"
          for="page-jump"
        >رفتن به صفحه</label>
        <input
          id="page-jump"
          v-model="jumpTo"
          inputmode="numeric"
          dir="ltr"
          placeholder="صفحه"
          class="h-8 w-16 rounded-md border bg-background px-2 text-center text-sm text-foreground"
        >
        <Button
          type="submit"
          variant="ghost"
          size="sm"
          :disabled="loading"
        >
          برو
        </Button>
      </form>
    </nav>
  </div>
</template>

<script setup lang="ts">
import { toPersianDigits } from '~/utils/jalali'

const props = defineProps<{ page: number, pageSize: number, total: number, loading?: boolean }>()
const emit = defineEmits<{ (e: 'update:page', v: number): void }>()

const fa = (n: number) => toPersianDigits(n)
const pageCount = computed(() => Math.max(1, Math.ceil(props.total / props.pageSize)))

/** 1 … (page-1) page (page+1) … last -- always shows the first and last page. */
const items = computed<(number | '…')[]>(() => {
  const last = pageCount.value
  const cur = props.page
  if (last <= 7) return Array.from({ length: last }, (_, i) => i + 1)
  const set = new Set<number>([1, last, cur, cur - 1, cur + 1])
  if (cur <= 3) [2, 3, 4].forEach(n => set.add(n))
  if (cur >= last - 2) [last - 1, last - 2, last - 3].forEach(n => set.add(n))
  const sorted = [...set].filter(n => n >= 1 && n <= last).sort((a, b) => a - b)
  const out: (number | '…')[] = []
  sorted.forEach((n, i) => {
    if (i > 0 && n - sorted[i - 1]! > 1) out.push('…')
    out.push(n)
  })
  return out
})

function go(p: number) {
  const next = Math.min(Math.max(1, p), pageCount.value)
  if (next !== props.page) emit('update:page', next)
}

const jumpTo = ref('')
function jump() {
  // accept Persian / Arabic digits too
  const latin = jumpTo.value.replace(/[۰-۹]/g, d => String('۰۱۲۳۴۵۶۷۸۹'.indexOf(d))).replace(/[٠-٩]/g, d => String('٠١٢٣٤٥٦٧٨٩'.indexOf(d)))
  const n = Number.parseInt(latin, 10)
  if (Number.isFinite(n)) go(n)
  jumpTo.value = ''
}
</script>
