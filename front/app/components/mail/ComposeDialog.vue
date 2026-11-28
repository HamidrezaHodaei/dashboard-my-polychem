<!--/components/mail/ComposeDialog.vue → <MailComposeDialog /> : new message / draft / forward -->
<script setup lang="ts">
import { ApiError } from '~/services/backendApi'
import type { MailFile, MailPerson } from '~/utils/mail'

export interface ComposeInit {
  draftId?: number | null
  to?: MailPerson[]
  cc?: MailPerson[]
  subject?: string
  body?: string
  attachments?: MailFile[]
  parentId?: number | null
}
const props = defineProps<{ open: boolean, init: ComposeInit }>()
const emit = defineEmits<{ 'update:open': [boolean], 'done': [] }>()

const store = useMailStore()
const notify = useNotify()

const to = ref<MailPerson[]>([])
const cc = ref<MailPerson[]>([])
const showCc = ref(false)
const subject = ref('')
const body = ref('')
const files = ref<MailFile[]>([])
const uploading = ref(0)
const draftId = ref<number | null>(null)
const sending = ref(false)
const dirty = ref(false)
const fileInput = ref<HTMLInputElement | null>(null)

watch(() => props.open, (v) => {
  if (!v) return
  to.value = [...(props.init.to || [])]
  cc.value = [...(props.init.cc || [])]
  showCc.value = cc.value.length > 0
  subject.value = props.init.subject || ''
  body.value = props.init.body || ''
  files.value = [...(props.init.attachments || [])]
  draftId.value = props.init.draftId ?? null
  dirty.value = false
}, { immediate: true })
watch([to, cc, subject, body, files], () => { dirty.value = true }, { deep: true })

const limits = computed(() => store.meta?.limits)
const totalSize = computed(() => files.value.reduce((s, f) => s + f.size, 0))
const hasContent = computed(() => !!(to.value.length || cc.value.length || subject.value.trim() || body.value.trim() || files.value.length))
const canSend = computed(() => (to.value.length || cc.value.length) && (body.value.trim() || files.value.length) && !sending.value && !uploading.value)

const payload = () => ({
  to: to.value.map(p => p.id),
  cc: cc.value.filter(p => !to.value.some(t => t.id === p.id)).map(p => p.id),
  subject: subject.value, body: body.value, attachment_ids: files.value.map(f => f.id),
  parent_id: props.init.parentId ?? null,
})

async function onPick(e: Event) {
  const input = e.target as HTMLInputElement
  const picked = Array.from(input.files || [])
  input.value = ''
  const max = limits.value?.max_files ?? 10
  for (const file of picked) {
    if (files.value.length >= max) { notify.warning(`حداکثر ${max.toLocaleString('fa-IR')} فایل پیوست مجاز است.`); break }
    if (limits.value && file.size > limits.value.max_file_mb * 1024 * 1024) {
      notify.error(`«${file.name}» بزرگ‌تر از ${limits.value.max_file_mb.toLocaleString('fa-IR')} مگابایت است.`)
      continue
    }
    uploading.value++
    try { files.value.push(await store.uploadFile(file)) }
    catch (err) { notify.error(`بارگذاری «${file.name}» ناموفق بود.`, err instanceof ApiError ? err.message : undefined) }
    finally { uploading.value-- }
  }
}
function dropFile(f: MailFile) {
  files.value = files.value.filter(x => x.id !== f.id)
  if (!draftId.value) store.removeUpload(f.id) // never attached to anything yet
}

async function send() {
  if (!canSend.value) return
  sending.value = true
  try {
    await store.send(payload(), draftId.value)
    notify.success('نامه ارسال شد.')
    dirty.value = false
    emit('update:open', false)
    emit('done')
  }
  catch (err) { notify.error('ارسال نامه ناموفق بود.', err instanceof ApiError ? err.message : undefined) }
  finally { sending.value = false }
}
async function saveDraft(silent = false) {
  try {
    const m = await store.saveDraft(payload(), draftId.value)
    draftId.value = m.id
    dirty.value = false
    if (!silent) notify.success('پیش‌نویس ذخیره شد.')
    return true
  }
  catch (err) { notify.error('ذخیرهٔ پیش‌نویس ناموفق بود.', err instanceof ApiError ? err.message : undefined); return false }
}
async function close(v: boolean) {
  if (v) return
  // closing a half-written message keeps it as a draft instead of losing it (and its uploads)
  if (dirty.value && hasContent.value && store.canCreate && !sending.value) {
    if (await saveDraft(true)) notify.info('پیش‌نویس ذخیره شد.')
  }
  emit('update:open', false)
}
</script>

<template>
  <Dialog :open="open" @update:open="close">
    <DialogContent dir="rtl" class="flex max-h-[90vh] flex-col gap-0 overflow-hidden rounded-md p-0 max-sm:top-0 max-sm:left-0 max-sm:h-dvh max-sm:max-h-dvh max-sm:w-screen max-sm:max-w-none max-sm:translate-x-0 max-sm:translate-y-0 max-sm:rounded-none sm:max-w-2xl">
      <DialogHeader class="border-b px-4 py-3 text-right sm:px-5">
        <DialogTitle class="text-base font-semibold">
          {{ init.parentId ? 'پاسخ' : init.subject?.startsWith('Fwd:') ? 'ارجاع نامه' : 'نامهٔ جدید' }}
        </DialogTitle>
        <DialogDescription class="sr-only">
          نوشتن و ارسال نامه به همکاران
        </DialogDescription>
      </DialogHeader>

      <div class="flex-1 space-y-3 overflow-y-auto px-4 py-4 sm:px-5">
        <div class="flex flex-col gap-1 sm:flex-row sm:items-start sm:gap-3">
          <span class="shrink-0 text-sm text-muted-foreground sm:w-14 sm:pt-2">گیرنده</span>
          <div class="min-w-0 flex-1">
            <MailRecipientPicker v-model="to" :exclude="cc.map(p => p.id)" />
          </div>
          <Button v-if="!showCc" variant="outline" type="button" class="h-11 sm:h-9" @click="showCc = true">
            افزودن رونوشت
          </Button>
        </div>
        <div v-if="showCc" class="flex flex-col gap-1 sm:flex-row sm:items-start sm:gap-3">
          <span class="shrink-0 text-sm text-muted-foreground sm:w-14 sm:pt-2">رونوشت</span>
          <div class="min-w-0 flex-1">
            <MailRecipientPicker v-model="cc" :exclude="to.map(p => p.id)" placeholder="افزودن گیرندهٔ رونوشت (بدون محدودیت تعداد)…" />
          </div>
        </div>
        <div class="flex flex-col gap-1 sm:flex-row sm:items-center sm:gap-3">
          <span class="shrink-0 text-sm text-muted-foreground sm:w-14">موضوع</span>
          <Input v-model="subject" dir="auto" maxlength="300" class="h-11 text-right placeholder:text-right sm:h-9" placeholder="موضوع نامه" />
        </div>
        <Textarea v-model="body" dir="auto" rows="10" class="text-right min-h-48 resize-y" placeholder="متن نامه را بنویسید" />

        <div v-if="files.length || uploading" class="space-y-1.5">
          <div v-for="f in files" :key="f.id" class="flex min-h-11 items-center gap-3 rounded-md border px-3 py-1.5 text-sm">
            <span class="min-w-0 flex-1 truncate" dir="auto">{{ f.name }}</span>
            <span class="shrink-0 text-xs tabular-nums text-muted-foreground">{{ formatFileSize(f.size) }}</span>
            <button type="button" class="shrink-0 px-2 py-2 text-destructive hover:underline" :aria-label="`حذف ${f.name}`" @click="dropFile(f)">
              حذف
            </button>
          </div>
          <p v-if="uploading" class="text-xs text-muted-foreground">
            در حال بارگذاری فایل…
          </p>
        </div>
      </div>

      <div class="flex flex-wrap items-center gap-2 border-t bg-muted/30 px-4 py-3 pb-[max(0.75rem,env(safe-area-inset-bottom))] sm:px-5">
        <input ref="fileInput" type="file" multiple class="hidden" :accept="limits?.allowed_extensions.join(',')" @change="onPick">
        <Button variant="outline" type="button" class="h-11 sm:h-9" :disabled="!!uploading" @click="fileInput?.click()">
          پیوست فایل
        </Button>
        <span v-if="limits" class="order-last w-full text-[11px] text-muted-foreground sm:order-none sm:w-auto">
          تا {{ limits.max_files.toLocaleString('fa-IR') }} فایل، هر کدام حداکثر {{ limits.max_file_mb.toLocaleString('fa-IR') }} مگابایت
          <template v-if="totalSize"> · مجموع {{ formatFileSize(totalSize) }}</template>
        </span>
        <div class="ms-auto flex gap-2">
          <Button variant="outline" type="button" class="h-11 sm:h-9" :disabled="!hasContent || sending" @click="saveDraft()">
            ذخیرهٔ پیش‌نویس
          </Button>
          <Button type="button" class="h-11 px-6 sm:h-9" :disabled="!canSend" @click="send">
            {{ sending ? 'در حال ارسال…' : 'ارسال' }}
          </Button>
        </div>
      </div>
    </DialogContent>
  </Dialog>
</template>
