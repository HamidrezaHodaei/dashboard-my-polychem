<template>
  <ContainerWrapper class="space-y-6 py-6 md:py-8">
    <AccessPageHeader
      title="درخواست پرداخت"
      description="درخواست‌هایی که پس از تأیید مدیر برای پرداخت ارجاع شده‌اند؛ ثبت پرداخت نقدی یا چکی هر کالا و بازگشت به تدارکات."
      section="مالی"
    />
    <div class="flex gap-2">
      <button v-for="t in TABS" :key="t.value" type="button" class="rounded-full border px-4 py-1.5 text-sm transition-colors hover:bg-muted" :class="tab === t.value && 'border-primary bg-primary/10 font-semibold'" @click="tab = t.value">{{ t.label }}</button>
    </div>
    <PurchasesFlowList :key="tab" base="/finance" :queue="tab" />
  </ContainerWrapper>
</template>

<script setup lang="ts">
const TABS = [{ value: 'finance', label: 'در انتظار پرداخت' }, { value: 'finance_done', label: 'پرداخت‌شده و پیگیری' }]
const tab = ref('finance')
</script>
