<!-- <PurchasesProductPicker :name :category-id @pick="p => ..." /> : choose a product from the purchase catalog.
     Typing only searches; the product is set when one is clicked (an item must come from the catalog). -->
<template>
  <div class="relative">
    <Input v-model="text" placeholder="جستجوی نام یا کد کالا…" :disabled="disabled" @focus="open = true; search()" @input="onType" @blur="close" />
    <ul v-if="open" class="absolute z-30 mt-1 max-h-56 w-full overflow-auto rounded-md border bg-background shadow">
      <li v-if="loading" class="px-3 py-2 text-xs text-muted-foreground">در حال جستجو…</li>
      <li v-for="p in options" :key="p.id" class="cursor-pointer px-3 py-2 text-sm hover:bg-muted" @mousedown.prevent="choose(p)">
        {{ p.name }}<span v-if="p.code" class="mr-2 text-xs text-muted-foreground" dir="ltr">{{ p.code }}</span>
      </li>
      <li v-if="!loading && !options.length" class="px-3 py-2 text-xs text-muted-foreground">
        کالایی پیدا نشد. {{ canManage ? 'می‌توانید آن را در «مدیریت کالاها» تعریف کنید.' : 'برای تعریف کالای جدید به مدیر سامانه اطلاع دهید.' }}
      </li>
    </ul>
  </div>
</template>

<script setup lang="ts">
import type { CatalogProduct } from '~/utils/purchase'

const props = defineProps<{ name: string, categoryId?: number | null, disabled?: boolean }>()
const emit = defineEmits<{ (e: 'pick', p: CatalogProduct | null): void }>()
const store = usePurchasesStore()
const canManage = computed(() => store.can('manage_catalog'))
const text = ref(props.name)
const options = ref<CatalogProduct[]>([])
const open = ref(false)
const loading = ref(false)
watch(() => props.name, v => { text.value = v })

let timer: ReturnType<typeof setTimeout> | undefined
function search() {
  clearTimeout(timer)
  timer = setTimeout(async () => {
    loading.value = true
    try { options.value = await store.searchProducts(text.value === props.name ? '' : text.value) }
    catch { options.value = [] }
    finally { loading.value = false }
  }, 200)
}
function onType() { open.value = true; search() }
function choose(p: CatalogProduct) { text.value = p.name; open.value = false; emit('pick', p) }
function close() { setTimeout(() => { open.value = false; text.value = props.name }, 120) } // unchosen text is discarded
</script>
