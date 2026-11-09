<!-- /components/request/ReviewDialog.vue  → <RequestReviewDialog /> : a manager decides on a request. -->
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
        <DialogTitle class="text-right">بررسی درخواست</DialogTitle>
        <DialogDescription
          dir="auto"
          class="text-right"
        >
          {{ title }} · وضعیت فعلی: {{ REQUEST_STATUS_LABELS[status] }}
        </DialogDescription>
      </DialogHeader>
      <div class="space-y-4 text-right">
        <div
          v-if="changeRequestNote"
          class="rounded-lg border border-amber-500/40 bg-amber-500/10 p-3 text-sm text-right"
        >
          <p class="mb-1 font-semibold text-right">
            درخواست تغییر از طرف ثبت‌کننده
          </p>
          <p
            dir="auto"
            class="whitespace-pre-wrap"
          >
            {{ changeRequestNote }}
          </p>
        </div>

        <div class="grid gap-2 text-right">
          <button
            v-for="o in options"
            :key="o.action"
            type="button"
            class="flex items-center justify-start gap-3 rounded-xl border-2 p-3 text-right transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            :class="action === o.action ? 'border-primary bg-primary/5' : 'border-border hover:border-muted-foreground/40'"
            :aria-pressed="action === o.action"
            @click="action = o.action"
          >
            <Icon
              :name="o.icon"
              class="size-5 shrink-0"
            />
            <span class="font-medium">{{ o.label }}</span>
          </button>
        </div>

        <div class="space-y-1.5 text-right">
          <Label class="block font-semibold text-right">
            توضیحات
            <span
              v-if="def?.noteRequired"
              class="text-destructive"
            >*</span>
            <span
              v-else
              class="text-xs font-normal text-muted-foreground"
            >(اختیاری)</span>
          </Label>
          <Textarea
            v-model="note"
            dir="auto"
            rows="3"
            class="text-right"
            placeholder="دلیل یا توضیح تصمیم..."
          />
          <p
            v-if="tried && def?.noteRequired && !note.trim()"
            class="text-xs text-destructive"
          >
            برای این تصمیم نوشتن توضیح الزامی است.
          </p>
          <p
            v-else-if="def?.hint"
            class="text-xs text-muted-foreground"
          >
            {{ def.hint }}
          </p>
        </div>
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
          :disabled="saving || !action"
          @click="submit"
        >
          {{ saving ? 'در حال ثبت...' : 'ثبت تصمیم' }}
        </Button>
      </DialogFooter>
    </DialogContent>
  </Dialog>
</template>

<script setup lang="ts">
import {
  REQUEST_REVIEW_ACTIONS, REQUEST_STATUS_LABELS, requestReviewActionsFor,
  type RequestReviewAction, type RequestStatusKey,
} from '~/utils/request-workflow'

const props = withDefaults(defineProps<{
  open: boolean
  title: string
  status: RequestStatusKey
  changeRequestNote?: string | null
  allowSuspend?: boolean
  saving?: boolean
}>(), { changeRequestNote: null, allowSuspend: false, saving: false })
const emit = defineEmits<{ 'update:open': [value: boolean], 'submit': [action: RequestReviewAction, note: string] }>()

const action = ref<RequestReviewAction | ''>('')
const note = ref('')
const tried = ref(false)

const options = computed(() =>
  requestReviewActionsFor(props.status, { allowSuspend: props.allowSuspend }).map(a => ({ action: a, ...REQUEST_REVIEW_ACTIONS[a] })))
const def = computed(() => (action.value ? REQUEST_REVIEW_ACTIONS[action.value] : null))

watch(() => props.open, (isOpen) => {
  if (!isOpen) return
  action.value = options.value[0]?.action ?? ''
  // a change request is usually answered by sending the record back for edits
  if (props.changeRequestNote && options.value.some(o => o.action === 'REQUEST_EDIT')) action.value = 'REQUEST_EDIT'
  note.value = ''
  tried.value = false
})

function submit() {
  if (!action.value) return
  tried.value = true
  if (def.value?.noteRequired && !note.value.trim()) return
  emit('submit', action.value, note.value.trim())
}
</script>
