<!-- /components/request/ChangeRequestDialog.vue  → <RequestChangeRequestDialog />
     The creator of a submitted request asks the manager to allow a change (reason required). -->
<template>
  <Dialog
    :open="open"
    @update:open="v => emit('update:open', v)"
  >
    <DialogContent
      dir="rtl"
      class="sm:max-w-md text-right"
    >
      <DialogHeader class="text-right">
        <DialogTitle class="text-right">درخواست تغییر اطلاعات</DialogTitle>
        <DialogDescription
          dir="auto"
          class="text-right"
        >
          «{{ title }}» ثبت نهایی شده و دیگر مستقیم قابل ویرایش نیست. دلیل نیاز به تغییر را برای مدیر بنویسید؛ در صورت موافقت، درخواست برای اصلاح به شما بازگردانده می‌شود.
        </DialogDescription>
      </DialogHeader>
      <div class="space-y-1.5 text-right">
        <Label class="block font-semibold text-right">دلیل درخواست تغییر <span class="text-destructive">*</span></Label>
        <Textarea
          v-model="reason"
          dir="auto"
          rows="4"
          class="text-right"
          placeholder="چه اطلاعاتی باید تغییر کند و چرا؟"
        />
        <p
          v-if="tried && reason.trim().length < 3"
          class="text-xs text-destructive"
        >
          دلیل را بنویسید (حداقل ۳ نویسه).
        </p>
      </div>
      <DialogFooter class="flex-row justify-between gap-2 sm:justify-between">
        <Button
          variant="ghost"
          :disabled="saving"
          @click="emit('update:open', false)"
        >
          انصراف
        </Button>
        <Button
          :disabled="saving"
          @click="submit"
        >
          {{ saving ? 'در حال ارسال...' : 'ارسال برای مدیر' }}
        </Button>
      </DialogFooter>
    </DialogContent>
  </Dialog>
</template>

<script setup lang="ts">
const props = withDefaults(defineProps<{ open: boolean, title: string, saving?: boolean }>(), { saving: false })
const emit = defineEmits<{ 'update:open': [value: boolean], 'submit': [reason: string] }>()

const reason = ref('')
const tried = ref(false)
watch(() => props.open, (isOpen) => {
  if (isOpen) {
    reason.value = ''
    tried.value = false
  }
})
function submit() {
  tried.value = true
  if (reason.value.trim().length < 3) return
  emit('submit', reason.value.trim())
}
</script>
