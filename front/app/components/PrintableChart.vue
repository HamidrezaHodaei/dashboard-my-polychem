<!-- <PrintableChart title="..." class="gap-4 p-5 shadow-none"> ...chart... </PrintableChart>
     A Card with a small toolbar: print this chart / save it as PDF (print dialog -> «Save as PDF»). -->
<template>
  <Card
    ref="root"
    class="relative"
  >
    <div class="print-hide absolute left-3 top-3 z-10 flex gap-0.5 opacity-50 transition-opacity hover:opacity-100">
      <Button
        variant="ghost"
        size="icon"
        class="size-7"
        title="چاپ نمودار"
        aria-label="چاپ نمودار"
        @click="print"
      >
        <Icon
          name="lucide:printer"
          class="size-4"
        />
      </Button>
      <Button
        variant="ghost"
        size="icon"
        class="size-7"
        title="دریافت PDF"
        aria-label="دریافت PDF"
        @click="pdf"
      >
        <Icon
          name="lucide:file-down"
          class="size-4"
        />
      </Button>
    </div>
    <slot />
  </Card>
</template>

<script setup lang="ts">
import { printElement } from '~/utils/printElement'

const props = defineProps<{ title?: string }>()
const root = ref<{ $el: HTMLElement } | null>(null)
const notify = useNotify()

const print = () => printElement(root.value?.$el, props.title)
function pdf() {
  notify.info('در پنجرهٔ چاپ، مقصد را «Save as PDF» انتخاب کنید.')
  printElement(root.value?.$el, props.title)
}
</script>
