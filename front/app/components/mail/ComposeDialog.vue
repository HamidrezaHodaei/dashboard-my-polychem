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
    <DialogContent dir="rtl" class="flex max-h-[90vh] flex-col gap-0 overflow-hidden p-0 sm:max-w-2xl">
      <DialogHeader class="border-b px-5 py-3 text-right">
        <DialogTitle class="text-base font-semibold">
          {{ init.parentId ? 'پاسخ' : init.subject?.startsWith('Fwd:') ? 'ارجاع نامه' : 'نامهٔ جدید' }}
        </DialogTitle>
        <DialogDescription class="sr-only">
          نوشتن و ارسال نامه به همکاران
        </DialogDescription>
      </DialogHeader>

      <div class="flex-1 space-y-3 overflow-y-auto px-5 py-4">
        <div class="flex items-start gap-3">
          <span class="w-12 shrink-0 pt-2 text-sm text-muted-foreground">به</span>
          <div class="min-w-0 flex-1">
            <MailRecipientPicker v-model="to" :exclude="cc.map(p => p.id)" />
          </div>
          <Button v-if="!showCc" variant="ghost" size="sm" type="button" @click="showCc = true">
            رونوشت
          </Button>
        </div>
        <div v-if="showCc" class="flex items-start gap-3">
          <span class="w-12 shrink-0 pt-2 text-sm text-muted-foreground">رونوشت</span>
          <div class="min-w-0 flex-1">
            <MailRecipientPicker v-model="cc" :exclude="to.map(p => p.id)" placeholder="افزودن گیرندهٔ رونوشت (بدون محدودیت تعداد)…" />
          </div>
        </div>
        <div class="flex items-center gap-3">
          <span class="w-12 shrink-0 text-sm text-muted-foreground">موضوع</span>
          <Input v-model="subject" dir="auto" maxlength="300" class="text-right placeholder:text-right" placeholder="موضوع نامه" />
        </div>
        <Textarea v-model="body" dir="auto" rows="10" class="text-right min-h-48 resize-y" placeholder="... متن نامه" />

        <div v-if="files.length || uploading" class="space-y-1.5">
          <div v-for="f in files" :key="f.id" class="flex items-center gap-2 rounded-md border px-3 py-1.5 text-sm">
            <Icon name="lucide:paperclip" class="size-4 text-muted-foreground" />
            <span class="min-w-0 flex-1 truncate" dir="auto">{{ f.name }}</span>
            <span class="text-xs text-muted-foreground">{{ formatFileSize(f.size) }}</span>
            <button type="button" class="text-muted-foreground hover:text-destructive" :aria-label="`حذف ${f.name}`" @click="dropFile(f)">
              <Icon name="lucide:x" class="size-4" />
            </button>
          </div>
          <p v-if="uploading" class="flex items-center gap-2 text-xs text-muted-foreground">
            <Icon name="lucide:loader-circle" class="size-3.5 animate-spin" /> در حال بارگذاری فایل…
          </p>
        </div>
      </div>

      <div class="flex flex-wrap items-center gap-2 border-t bg-muted/30 px-5 py-3">
        <input ref="fileInput" type="file" multiple class="hidden" :accept="limits?.allowed_extensions.join(',')" @change="onPick">
        <Button variant="outline" size="sm" type="button" class="gap-1.5" :disabled="!!uploading" @click="fileInput?.click()">
          <Icon name="lucide:paperclip" class="size-4" /> پیوست
        </Button>
        <span v-if="limits" class="text-[11px] text-muted-foreground">
          تا {{ limits.max_files.toLocaleString('fa-IR') }} فایل، هر کدام حداکثر {{ limits.max_file_mb.toLocaleString('fa-IR') }} مگابایت
          <template v-if="totalSize"> · مجموع {{ formatFileSize(totalSize) }}</template>
        </span>
        <div class="ms-auto flex gap-2">
          <Button variant="outline" size="sm" type="button" :disabled="!hasContent || sending" @click="saveDraft()">
            ذخیرهٔ پیش‌نویس
          </Button>
          <Button size="sm" type="button" class="gap-1.5" :disabled="!canSend" @click="send">
            <Icon :name="sending ? 'lucide:loader-circle' : 'lucide:send'" class="size-4" :class="sending && 'animate-spin'" />
            ارسال
          </Button>
        </div>
      </div>
    </DialogContent>
  </Dialog>
</template>
