<template>
  <div class="relative flex flex-col items-center justify-center h-dvh text-center">
    <div class="z-20 w-full max-w-lg px-4 mx-auto mb-16 sm:px-6 lg:px-8">
      <span class="font-medium leading-none text-5xl md:text-7xl lg:text-9xl text-primary-content">403</span>
      <h2 class="my-2 text-2xl font-bold tracking-tight md:text-3xl">
        دسترسی مجاز نیست
      </h2>
      <p class="text-muted-foreground">
        شما مجوز مشاهده این بخش را ندارید. اگر فکر می‌کنید این پیام اشتباه است، با مدیر سامانه تماس بگیرید.
      </p>
      <div class="mt-8">
        <Button size="lg" as-child>
          <NuxtLink to="/">
            <Icon name="lucide:arrow-left" class="text-base size-4" aria-hidden="true" />
            بازگشت به صفحه اصلی
          </NuxtLink>
        </Button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
definePageMeta({ layout: 'blank' })
usePageSeoMeta({ title: 'دسترسی مجاز نیست' })
</script>
