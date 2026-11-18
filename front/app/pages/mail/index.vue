<!--/pages/mail/index.vue : مکاتبات سازمانی (internal correspondence). Layout follows the reference mail app
(folders + labels | message list | conversation + reply); colours, fonts and controls come from this
project's own theme tokens. All data and permissions come from /api/mail. -->
<script setup lang="ts">
import type { ComposeInit } from '~/components/mail/ComposeDialog.vue'
import { ApiError } from '~/services/backendApi'
import type { MailFile, MailFolder, MailLabel, MailMessage, MailPerson } from '~/utils/mail'

definePageMeta({ title: 'مکاتبات' })

const store = useMailStore()
const route = useRoute()
const notify = useNotify()

const composeOpen = ref(false)
const composeInit = ref<ComposeInit>({})
const unitsOpen = ref(false)
const showAllMessages = ref(false)
const replyBody = ref('')
const replyAll = ref(false)
const replyFiles = ref<MailFile[]>([])
const replyUploading = ref(false)
const replySending = ref(false)
const replyInput = ref<HTMLInputElement | null>(null)
const ready = ref(false)

const viewTitle = computed(() => {
  const v = store.view
  if (v.kind === 'folder') return MAIL_FOLDERS.find(f => f.id === v.folder)?.label
  if (v.kind === 'label') return labelStyle(v.label)?.label
  return 'ستاره‌دار'
})
const folder = computed<MailFolder | null>(() => (store.view.kind === 'folder' ? store.view.folder : null))
const threadFolder = computed(() => store.thread?.folder ?? folder.value)

onMounted(async () => {
  try {
    await store.loadMeta()
    if (store.canRead) {
      await Promise.all([store.loadList(), store.refreshCounters()])
      const id = Number(route.query.thread)
      if (id) await open(id)
    }
  }
  catch (e) { notify.error('بارگذاری مکاتبات ناموفق بود.', e instanceof ApiError ? e.message : undefined) }
  finally { ready.value = true }
})

// a notification link (/mail?thread=ID) clicked while the page is already open
watch(() => route.query.thread, (v) => { const id = Number(v); if (id && ready.value) open(id) })

let searchTimer: ReturnType<typeof setTimeout> | undefined
watch(() => store.search, () => { clearTimeout(searchTimer); searchTimer = setTimeout(() => store.loadList(), 300) })
watch(() => [store.unreadOnly, store.sort], () => store.loadList())

async function guard<T>(fn: () => Promise<T>, failure: string) {
  try { return await fn() }
  catch (e) { notify.error(failure, e instanceof ApiError ? e.message : undefined) }
}

async function open(id: number) {
  showAllMessages.value = false
  replyBody.value = ''
  replyFiles.value = []
  replyAll.value = false
  await guard(async () => {
    await store.openThread(id)
    if (folder.value === 'drafts' && store.thread?.messages[0]?.is_draft) editDraft(store.thread.messages[0])
  }, 'باز کردن نامه ناموفق بود.')
}

const people = (ids: number[]): MailPerson[] => ids.map(i => store.people[i]).filter(Boolean) as MailPerson[]
const nameOf = (id: number) => store.people[id]?.full_name || 'کاربر حذف‌شده'

function newMail() {
  composeInit.value = {}
  composeOpen.value = true
}
function editDraft(m: MailMessage) {
  composeInit.value = {
    draftId: m.id, to: people(m.to), cc: people(m.cc), subject: m.subject, body: m.body,
    attachments: m.attachments, parentId: m.parent_id,
  }
  composeOpen.value = true
}
function forward(m: MailMessage) {
  const quoted = `\n\n---------- نامهٔ ارجاع‌شده ----------\nاز: ${nameOf(m.sender_id)}\nتاریخ: ${formatMailDateLong(m.sent_at)}\nموضوع: ${m.subject}\n\n${m.body}`
  composeInit.value = { subject: m.subject.startsWith('Fwd:') ? m.subject : `Fwd: ${m.subject}`, body: quoted, attachments: m.attachments }
  composeOpen.value = true
}

const lastMessage = computed(() => store.thread?.messages.at(-1))
const visibleMessages = computed(() => {
  const all = store.thread?.messages || []
  return showAllMessages.value || all.length <= 2 ? all : all.slice(-1)
})
const hiddenCount = computed(() => (store.thread?.messages.length || 0) - visibleMessages.value.length)

async function pickReplyFiles(e: Event) {
  const input = e.target as HTMLInputElement
  const picked = Array.from(input.files || [])
  input.value = ''
  replyUploading.value = true
  for (const f of picked) {
    if (replyFiles.value.length >= (store.meta?.limits.max_files ?? 10)) break
    await guard(async () => { replyFiles.value.push(await store.uploadFile(f)) }, `بارگذاری «${f.name}» ناموفق بود.`)
  }
  replyUploading.value = false
}
async function sendReply() {
  const target = lastMessage.value
  if (!target || (!replyBody.value.trim() && !replyFiles.value.length)) return
  replySending.value = true
  const ok = await guard(async () => {
    await store.reply(target.id, { body: replyBody.value, reply_all: replyAll.value, attachment_ids: replyFiles.value.map(f => f.id) })
    return true
  }, 'ارسال پاسخ ناموفق بود.')
  replySending.value = false
  if (ok) { replyBody.value = ''; replyFiles.value = []; notify.success('پاسخ ارسال شد.') }
}

const unreadCount = computed(() => store.counters.folders[folder.value || 'inbox']?.unread || 0)
const toggleLabel = (l: MailLabel) => {
  const cur = store.thread?.labels || []
  guard(() => store.setLabels(store.selectedId!, cur.includes(l) ? cur.filter(x => x !== l) : [...cur, l]), 'تغییر برچسب ناموفق بود.')
}
const act = (fn: () => Promise<unknown>, msg: string) => guard(fn, msg)
const canManage = computed(() => !!store.meta?.can_manage_access)
</script>

<template>
  <div class="mail-page flex h-full min-h-0 overflow-hidden rounded-lg border border-border bg-card shadow-sm" dir="rtl">
    <p v-if="ready && !store.canRead" class="m-auto p-10 text-sm text-muted-foreground">
      شما به بخش مکاتبات دسترسی ندارید.
    </p>

    <template v-else>
      <!-- folders + labels -->
      <aside class="hidden w-56 shrink-0 flex-col border-e border-border bg-muted/20 p-3 lg:flex">
        <Button v-if="store.canCreate" class="mb-4 w-full gap-2" @click="newMail">
          <Icon name="lucide:pen-line" class="size-4" /> نامهٔ جدید
        </Button>
        <p class="px-2 pb-1 text-[11px] font-medium text-muted-foreground">
          پوشه‌ها
        </p>
        <button
          v-for="f in MAIL_FOLDERS"
          :key="f.id"
          class="flex items-center gap-2.5 rounded-md px-2.5 py-2 text-sm transition-colors hover:bg-accent"
          :class="store.view.kind === 'folder' && store.view.folder === f.id && 'bg-accent font-medium'"
          @click="store.setView({ kind: 'folder', folder: f.id })"
        >
          <Icon :name="f.icon" class="size-4 text-muted-foreground" />
          <span class="flex-1 text-start">{{ f.label }}</span>
          <span v-if="store.folderBadge(f.id)" class="text-xs text-muted-foreground">{{ store.folderBadge(f.id).toLocaleString('fa-IR') }}</span>
        </button>
        <button
          class="flex items-center gap-2.5 rounded-md px-2.5 py-2 text-sm transition-colors hover:bg-accent"
          :class="store.view.kind === 'starred' && 'bg-accent font-medium'"
          @click="store.setView({ kind: 'starred' })"
        >
          <Icon name="lucide:star" class="size-4 text-muted-foreground" />
          <span class="flex-1 text-start">ستاره‌دار</span>
        </button>

        <Separator class="my-3" />
        <p class="px-2 pb-1 text-[11px] font-medium text-muted-foreground">
          برچسب‌ها
        </p>
        <button
          v-for="l in MAIL_LABELS"
          :key="l.id"
          class="flex items-center gap-2.5 rounded-md px-2.5 py-2 text-sm transition-colors hover:bg-accent"
          :class="store.view.kind === 'label' && store.view.label === l.id && 'bg-accent font-medium'"
          @click="store.setView({ kind: 'label', label: l.id })"
        >
          <span class="size-2.5 rounded-full" :class="l.color" />
          <span class="flex-1 text-start">{{ l.label }}</span>
          <span v-if="store.counters.labels[l.id]" class="text-xs text-muted-foreground">{{ store.counters.labels[l.id]!.toLocaleString('fa-IR') }}</span>
        </button>

        <Button v-if="canManage" variant="ghost" size="sm" class="mt-auto justify-start gap-2 text-muted-foreground" @click="unitsOpen = true">
          <Icon name="lucide:building-2" class="size-4" /> دسترسی واحدها
        </Button>
      </aside>

      <!-- list -->
      <section class="flex w-full min-w-0 flex-col border-e border-border md:w-[22rem] md:shrink-0" :class="store.selectedId && 'hidden md:flex'">
        <div class="flex items-center justify-between gap-2 px-4 pt-4 pb-3">
          <h2 class="text-lg font-semibold">
            {{ viewTitle }}
          </h2>
          <div class="flex items-center gap-1 rounded-lg bg-muted p-0.5 text-xs">
            <button class="rounded-md px-2.5 py-1" :class="!store.unreadOnly && 'bg-background shadow-sm'" @click="store.unreadOnly = false">
              همه
            </button>
            <button class="rounded-md px-2.5 py-1" :class="store.unreadOnly && 'bg-background shadow-sm'" @click="store.unreadOnly = true">
              نخوانده<template v-if="unreadCount"> ({{ unreadCount.toLocaleString('fa-IR') }})</template>
            </button>
          </div>
        </div>
        <div class="flex gap-2 px-4 pb-3">
          <div class="relative flex-1">
            <Icon name="lucide:search" class="absolute start-2.5 top-2.5 size-4 text-muted-foreground" />
            <Input v-model="store.search" dir="auto" class="text-right ps-8" placeholder="جست‌وجو در نامه‌ها" />
          </div>
          <Button variant="outline" size="icon" title="مرتب‌سازی" @click="store.sort = store.sort === 'newest' ? 'oldest' : 'newest'">
            <Icon name="lucide:arrow-up-down" class="size-4" />
          </Button>
          <Button v-if="store.canCreate" class="lg:hidden" size="icon" title="نامهٔ جدید" @click="newMail">
            <Icon name="lucide:pen-line" class="size-4" />
          </Button>
        </div>

        <div class="flex gap-1 overflow-x-auto px-4 pb-2 lg:hidden">
          <button
            v-for="f in MAIL_FOLDERS"
            :key="f.id"
            class="shrink-0 rounded-full border px-3 py-1 text-xs"
            :class="store.view.kind === 'folder' && store.view.folder === f.id && 'bg-accent'"
            @click="store.setView({ kind: 'folder', folder: f.id })"
          >
            {{ f.label }}
          </button>
        </div>

        <div class="min-h-0 flex-1 overflow-y-auto px-2 pb-2">
          <p v-if="store.error" class="p-6 text-center text-sm text-destructive">
            {{ store.error }}
          </p>
          <p v-else-if="store.loading && !store.rows.length" class="p-6 text-center text-sm text-muted-foreground">
            در حال بارگذاری…
          </p>
          <p v-else-if="!store.rows.length" class="p-10 text-center text-sm text-muted-foreground">
            نامه‌ای وجود ندارد.
          </p>
          <button
            v-for="row in store.rows"
            :key="row.id"
            class="mb-1 flex w-full gap-3 rounded-lg border border-transparent p-3 text-start transition-colors hover:bg-accent/60"
            :class="store.selectedId === row.id && 'border-border bg-accent'"
            @click="open(row.id)"
          >
            <MailPersonAvatar :person="store.person(row.sender_id)" size="size-10" />
            <div class="min-w-0 flex-1">
              <div class="flex items-center gap-2">
                <span class="min-w-0 flex-1 truncate text-sm" :class="!row.is_read && 'font-bold'">
                  {{ row.is_draft ? 'پیش‌نویس' : (row.is_mine ? 'من' : nameOf(row.sender_id)) }}
                </span>
                <Icon v-if="row.is_starred" name="lucide:star" class="size-3.5 fill-current" />
                <span class="shrink-0 text-[11px] text-muted-foreground">{{ formatMailDate(row.sent_at || row.created_at) }}</span>
              </div>
              <div class="flex items-center gap-1.5">
                <span class="truncate text-xs" :class="row.is_read ? 'text-foreground/80' : 'font-semibold'" dir="auto">{{ row.subject || '(بدون موضوع)' }}</span>
                <span v-if="row.thread_count > 1" class="text-xs text-muted-foreground">({{ row.thread_count.toLocaleString('fa-IR') }})</span>
                <Icon v-if="row.has_attachments" name="lucide:paperclip" class="size-3 shrink-0 text-muted-foreground" />
                <span class="ms-auto flex gap-1">
                  <span v-for="l in row.labels" :key="l" class="size-2 rounded-full" :class="labelStyle(l)?.color" />
                </span>
              </div>
              <p class="mt-0.5 line-clamp-1 text-xs text-muted-foreground" dir="auto">
                {{ row.preview }}
              </p>
            </div>
          </button>
          <Button v-if="store.hasMore" variant="ghost" class="w-full" :disabled="store.loading" @click="store.loadMore()">
            نمایش بیشتر
          </Button>
        </div>
      </section>

      <!-- conversation -->
      <section class="min-w-0 flex-1 flex-col" :class="store.selectedId ? 'flex' : 'hidden md:flex'">
        <div v-if="!store.thread" class="m-auto flex flex-col items-center gap-2 p-10 text-sm text-muted-foreground">
          <Icon name="lucide:mail-open" class="size-10 opacity-40" />
          {{ store.threadLoading ? 'در حال بارگذاری…' : 'یک نامه را انتخاب کنید.' }}
        </div>

        <template v-else>
          <div class="flex flex-wrap items-center gap-1 border-b px-3 py-2">
            <Button variant="ghost" size="icon" class="md:hidden" @click="store.selectedId = null; store.thread = null">
              <Icon name="lucide:arrow-right" class="size-4" />
            </Button>
            <template v-if="threadFolder === 'trash' || threadFolder === 'spam'">
              <Button v-if="store.canUpdate" variant="ghost" size="sm" class="gap-1.5" @click="act(() => store.move(store.selectedId!, 'inbox'), 'بازیابی ناموفق بود.')">
                <Icon name="lucide:undo-2" class="size-4" /> بازیابی
              </Button>
              <Button v-if="store.canDelete" variant="ghost" size="sm" class="gap-1.5 text-destructive" @click="act(() => store.deletePermanently(store.selectedId!), 'حذف ناموفق بود.')">
                <Icon name="lucide:trash-2" class="size-4" /> حذف دائمی
              </Button>
            </template>
            <template v-else-if="threadFolder !== 'drafts'">
              <Button v-if="store.canUpdate" variant="ghost" size="icon" title="بایگانی" @click="act(() => store.move(store.selectedId!, 'archive'), 'بایگانی ناموفق بود.')">
                <Icon name="lucide:archive" class="size-4" />
              </Button>
              <Button v-if="store.canUpdate" variant="ghost" size="icon" title="هرزنامه" @click="act(() => store.move(store.selectedId!, 'spam'), 'انتقال ناموفق بود.')">
                <Icon name="lucide:shield-alert" class="size-4" />
              </Button>
              <Button v-if="store.canDelete" variant="ghost" size="icon" title="سطل زباله" @click="act(() => store.move(store.selectedId!, 'trash'), 'انتقال به سطل زباله ناموفق بود.')">
                <Icon name="lucide:trash-2" class="size-4" />
              </Button>
              <DropdownMenu v-if="store.canUpdate">
                <DropdownMenuTrigger as-child>
                  <Button variant="ghost" size="icon" title="برچسب">
                    <Icon name="lucide:tag" class="size-4" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="start" dir="rtl">
                  <DropdownMenuCheckboxItem
                    v-for="l in MAIL_LABELS"
                    :key="l.id"
                    :model-value="store.thread.labels.includes(l.id)"
                    @select.prevent="toggleLabel(l.id)"
                  >
                    <span class="me-2 size-2 rounded-full" :class="l.color" /> {{ l.label }}
                  </DropdownMenuCheckboxItem>
                </DropdownMenuContent>
              </DropdownMenu>
              <Button
                v-if="store.canUpdate" variant="ghost" size="icon" title="ستاره"
                @click="act(() => store.setFlags(store.selectedId!, { is_starred: !store.thread!.is_starred }), 'تغییر ناموفق بود.')"
              >
                <Icon name="lucide:star" class="size-4" :class="store.thread.is_starred && 'fill-current'" />
              </Button>
              <Button
                v-if="store.canUpdate" variant="ghost" size="icon" title="علامت‌گذاری به‌عنوان نخوانده"
                @click="act(() => store.setFlags(store.selectedId!, { is_read: false }), 'تغییر ناموفق بود.')"
              >
                <Icon name="lucide:mail" class="size-4" />
              </Button>
            </template>
            <span v-else-if="store.canDelete" class="contents">
              <Button variant="ghost" size="sm" class="gap-1.5 text-destructive" @click="act(() => store.discardDraft(store.selectedId!), 'حذف پیش‌نویس ناموفق بود.')">
                <Icon name="lucide:trash-2" class="size-4" /> حذف پیش‌نویس
              </Button>
            </span>
            <div v-if="store.thread.labels.length" class="ms-auto flex gap-1">
              <span v-for="l in store.thread.labels" :key="l" class="flex items-center gap-1 rounded-full border px-2 py-0.5 text-[11px]">
                <span class="size-1.5 rounded-full" :class="labelStyle(l)?.color" />{{ labelStyle(l)?.label }}
              </span>
            </div>
          </div>

          <div class="min-h-0 flex-1 overflow-y-auto p-5">
            <h3 class="mb-4 text-lg font-semibold" dir="auto">
              {{ store.thread.subject }}
            </h3>
            <button
              v-if="hiddenCount > 0"
              class="mb-4 flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"
              @click="showAllMessages = true"
            >
              <Icon name="lucide:chevron-down" class="size-4" /> {{ hiddenCount.toLocaleString('fa-IR') }} پیام قبلی
            </button>

            <article v-for="m in visibleMessages" :key="m.id" class="mb-5 rounded-lg border p-4">
              <header class="flex items-start gap-3">
                <MailPersonAvatar :person="store.person(m.sender_id)" size="size-10" />
                <div class="min-w-0 flex-1">
                  <div class="flex items-center gap-2">
                    <span class="truncate text-sm font-semibold">{{ nameOf(m.sender_id) }}</span>
                    <span class="ms-auto shrink-0 text-xs text-muted-foreground">{{ formatMailDateLong(m.sent_at || m.created_at) }}</span>
                  </div>
                  <p class="truncate text-xs text-muted-foreground" dir="ltr">
                    {{ store.person(m.sender_id)?.email }}
                  </p>
                  <p class="mt-1 text-xs text-muted-foreground">
                    <span>به: {{ m.to.map(nameOf).join('، ') }}</span>
                    <span v-if="m.cc.length"> · رونوشت: {{ m.cc.map(nameOf).join('، ') }}</span>
                  </p>
                </div>
              </header>
              <div class="mt-4 text-sm leading-7 whitespace-pre-wrap" dir="auto">
                {{ m.body }}
              </div>
              <div v-if="m.attachments.length" class="mt-4 flex flex-wrap gap-2 border-t pt-3">
                <button
                  v-for="f in m.attachments"
                  :key="f.id"
                  class="flex items-center gap-2 rounded-md border px-3 py-1.5 text-xs hover:bg-accent"
                  @click="act(() => store.downloadFile(f), 'دانلود فایل ناموفق بود.')"
                >
                  <Icon name="lucide:paperclip" class="size-3.5" />
                  <span class="max-w-48 truncate" dir="auto">{{ f.name }}</span>
                  <span class="text-muted-foreground">{{ formatFileSize(f.size) }}</span>
                  <Icon name="lucide:download" class="size-3.5 text-muted-foreground" />
                </button>
              </div>
              <footer v-if="store.canCreate && !m.is_draft" class="mt-3 flex justify-end">
                <Button variant="ghost" size="sm" class="gap-1.5" @click="forward(m)">
                  <Icon name="lucide:forward" class="size-4" /> ارجاع
                </Button>
              </footer>
            </article>
          </div>

          <!-- quick reply -->
          <div v-if="store.canCreate && threadFolder !== 'drafts' && threadFolder !== 'trash'" class="border-t p-4">
            <div class="rounded-lg border">
              <Textarea v-model="replyBody" dir="rtl" rows="3" class="resize-none border-0 shadow-none focus-visible:ring-0" :placeholder="`پاسخ به ${nameOf(lastMessage!.is_mine ? (lastMessage!.to[0] ?? 0) : lastMessage!.sender_id)}…`" />
              <div v-if="replyFiles.length" class="flex flex-wrap gap-1.5 px-3 pb-2">
                <span v-for="f in replyFiles" :key="f.id" class="flex items-center gap-1 rounded-full bg-muted px-2 py-0.5 text-xs">
                  {{ f.name }}
                  <button @click="replyFiles = replyFiles.filter(x => x.id !== f.id); store.removeUpload(f.id)">
                    <Icon name="lucide:x" class="size-3" />
                  </button>
                </span>
              </div>
              <div class="flex flex-wrap items-center gap-3 border-t px-3 py-2">
                <input ref="replyInput" type="file" multiple class="hidden" @change="pickReplyFiles">
                <Button variant="ghost" size="icon-sm" title="پیوست" :disabled="replyUploading" @click="replyInput?.click()">
                  <Icon name="lucide:paperclip" class="size-4" />
                </Button>
                <label class="flex cursor-pointer items-center gap-2 text-xs text-muted-foreground">
                  <Switch v-model="replyAll" /> پاسخ به همه
                </label>
                <label v-if="store.canUpdate" class="flex cursor-pointer items-center gap-2 text-xs text-muted-foreground">
                  <Switch :model-value="store.thread.is_muted" @update:model-value="v => act(() => store.setFlags(store.selectedId!, { is_muted: !!v }), 'تغییر ناموفق بود.')" />
                  بی‌صدا کردن گفتگو
                </label>
                <Button size="sm" class="ms-auto gap-1.5" :disabled="replySending || replyUploading || (!replyBody.trim() && !replyFiles.length)" @click="sendReply">
                  ارسال <Icon name="lucide:send" class="size-4" />
                </Button>
              </div>
            </div>
          </div>
        </template>
      </section>
    </template>

    <MailComposeDialog v-model:open="composeOpen" :init="composeInit" />
    <MailUnitAccessDialog v-model:open="unitsOpen" />
  </div>
</template>
