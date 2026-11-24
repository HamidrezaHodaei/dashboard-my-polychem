<template>
  <ContainerWrapper class="space-y-6 py-6 md:py-8">
    <NuxtLink to="/inventory" class="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"><Icon name="lucide:chevron-right" class="size-4" />درخواست‌های خرید</NuxtLink>
    <div>
      <h1 class="text-2xl font-semibold tracking-tight">ثبت درخواست خرید</h1>
      <p class="mt-1 text-sm text-muted-foreground">اقلام مورد نیاز را وارد کنید؛ بعد از ثبت، پیگیری وضعیت هر قلم از صفحهٔ درخواست انجام می‌شود.</p>
    </div>
    <p v-if="!store.meta?.my_permissions.warehouse" class="rounded-lg border bg-muted/40 p-4 text-sm text-muted-foreground">مجوز ثبت درخواست خرید برای حساب شما فعال نیست.</p>
    <PurchasesFlowForm v-else @saved="r => navigateTo(`/inventory/${r.id}`)" />
  </ContainerWrapper>
</template>

<script setup lang="ts">
const store = usePurchaseFlowStore()
await store.loadMeta()
</script>
