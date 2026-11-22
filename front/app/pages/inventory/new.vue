<template>
  <ContainerWrapper class="space-y-6 py-6 md:py-8">
    <NuxtLink to="/inventory" class="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"><Icon name="lucide:chevron-right" class="size-4" />انبار / درخواست خرید</NuxtLink>
    <h1 class="text-2xl font-semibold tracking-tight">ثبت درخواست خرید</h1>
    <PurchasesFlowForm @saved="r => navigateTo(`/inventory/${r.id}`)" />
  </ContainerWrapper>
</template>
