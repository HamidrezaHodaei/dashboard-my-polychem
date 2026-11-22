<!-- <PurchasesFlowPage back="/inventory" back-label="انبار" /> : loads the request of the route (`id`) and shows it
     (detail ↔ the correction form for the warehouse). Shared by the warehouse, procurement and finance pages. -->
<template>
  <ContainerWrapper class="space-y-5 py-6 md:py-8">
    <NuxtLink :to="back" class="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"><Icon name="lucide:chevron-right" class="size-4" />{{ backLabel }}</NuxtLink>
    <p v-if="error" class="rounded-lg border border-destructive/40 bg-destructive/5 p-3 text-sm text-destructive">{{ error }}</p>
    <div v-else-if="!req" class="p-10 text-center text-muted-foreground">در حال بارگذاری…</div>
    <template v-else>
      <PurchasesFlowForm v-if="editing" :edit="req" @saved="r => { req = r; editing = false }" />
      <PurchasesFlowDetail v-else :request="req" @updated="r => req = r" @edit="editing = true" />
    </template>
  </ContainerWrapper>
</template>

<script setup lang="ts">
import type { FlowRequest } from '~/utils/purchaseFlow'

defineProps<{ back: string, backLabel: string }>()
const store = usePurchaseFlowStore()
const route = useRoute()
const req = ref<FlowRequest | null>(null)
const error = ref('')
const editing = ref(false)
onMounted(async () => {
  try { await store.loadMeta(); req.value = await store.fetchOne(Number(route.params.id)) }
  catch (e: any) { error.value = e?.message || 'بارگذاری درخواست انجام نشد.' }
})
</script>
