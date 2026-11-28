<!--/pages/mail/index.vue : مکاتبات سازمانی (internal correspondence).
Formal office-automation layout, driven by this project's own theme tokens:
  - ≥1280px : folders | correspondence table/list | letter (three panes)
  - 768-1279: folders | table; opening a letter replaces the table (with «بازگشت»)
  - <768px  : one pane at a time -- folder selector + stacked list, then a full-screen letter with a bottom action bar
All data and permissions come from /api/mail; nothing about the business logic changed. -->
<script setup lang="ts">
import { useMediaQuery } from '@vueuse/core'
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
const replyBox = ref<HTMLElement | null>(null)
const ready = ref(false)

// layout mode
const isWide = useMediaQuery('(min-width: 1280px)')
const isMd = useMediaQuery('(min-width: 768px)')
const splitView = computed(() => !!store.selectedId && isWide.value) // list + letter side by side
const detailOnly = computed(() => !!store.selectedId && !isWide.value) // the letter replaces the list
const tableMode = computed(() => isMd.value && !splitView.value) // wide table vs. compact rows

const viewTitle = computed(() => {
  const v = store.view
  if (v.kind === 'folder') return MAIL_FOLDERS.find(f => f.id === v.folder)?.label
  if (v.kind === 'label') return labelStyle(v.label)?.label
  return 'ستاره‌دار'
})
const folder = computed<MailFolder | null>(() => (store.view.kind === 'folder' ? store.view.folder : null))
const threadFolder = computed(() => store.thread?.folder ?? folder.value)

// folder selector for phones (a native select: reliable, touch friendly, never overflows)
const viewKey = computed({
  get: () => (store.view.kind === 'folder' ? `folder:${store.view.folder}` : store.view.kind === 'label' ? `label:${store.view.label}` : 'starred'),
  set: (v: string) => {
    const [kind, id] = v.split(':')
    if (kind === 'folder') store.setView({ kind: 'folder', folder: id as MailFolder })
    else if (kind === 'label') store.setView({ kind: 'label', label: id as MailLabel })
    else store.setView({ kind: 'starred' })
  },
})
const selectClass = 'h-11 w-full rounded-md border border-input bg-background px-3 text-sm md:h-9 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/40'

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
onBeforeUnmount(() => clearTimeout(searchTimer))

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
function backToList() {
  store.selectedId = null
  store.thread = null
}

const people = (ids: number[]): MailPerson[] => ids.map(i => store.people[i]).filter(Boolean) as MailPerson[]
const nameOf = (id: number) => store.people[id]?.full_name || 'کاربر حذف‌شده'
const namesOf = (ids: number[]) => ids.map(nameOf).join('، ')
/** Sender column of the list: who wrote it -- or, for mail I wrote, who it went to. */
function counterparty(row: { is_draft: boolean, is_mine: boolean, sender_id: number, to: number[] }) {
  if (row.is_draft) return row.to.length ? `پیش‌نویس · به: ${namesOf(row.to.slice(0, 2))}` : 'پیش‌نویس'
  if (row.is_mine) return row.to.length ? `به: ${namesOf(row.to.slice(0, 2))}${row.to.length > 2 ? ` و ${toPersianDigits(row.to.length - 2)} نفر دیگر` : ''}` : 'من'
  return nameOf(row.sender_id)
}

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
const canReply = computed(() => store.canCreate && !!store.thread && threadFolder.value !== 'drafts' && threadFolder.value !== 'trash')
const canLabel = computed(() => store.canUpdate && !!store.thread && !['trash', 'spam', 'drafts'].includes(threadFolder.value || ''))

function focusReply() {
  replyBox.value?.scrollIntoView({ block: 'center', behavior: 'smooth' })
  replyBox.value?.querySelector('textarea')?.focus({ preventScroll: true })
}

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

/** Operations on the open letter. One list drives the desktop toolbar AND the phone «بیشتر» menu. */
interface ThreadAction { key: string, label: string, danger?: boolean, run: () => void }
const threadActions = computed<ThreadAction[]>(() => {
  const id = store.selectedId
  const t = store.thread
  if (!id || !t) return []
  const f = threadFolder.value
  const out: ThreadAction[] = []
  if (f === 'trash' || f === 'spam') {
    if (store.canUpdate) out.push({ key: 'restore', label: 'بازیابی', run: () => act(() => store.move(id, 'inbox'), 'بازیابی ناموفق بود.') })
    if (store.canDelete) out.push({ key: 'purge', label: 'حذف دائمی', danger: true, run: () => act(() => store.deletePermanently(id), 'حذف ناموفق بود.') })
  }
  else if (f === 'drafts') {
    if (store.canDelete) out.push({ key: 'discard', label: 'حذف پیش‌نویس', danger: true, run: () => act(() => store.discardDraft(id), 'حذف پیش‌نویس ناموفق بود.') })
  }
  else {
    if (store.canUpdate) {
      out.push({ key: 'archive', label: 'بایگانی', run: () => act(() => store.move(id, 'archive'), 'بایگانی ناموفق بود.') })
      out.push({ key: 'spam', label: 'انتقال به هرزنامه', run: () => act(() => store.move(id, 'spam'), 'انتقال ناموفق بود.') })
      out.push({ key: 'star', label: t.is_starred ? 'حذف ستاره' : 'ستاره‌دار کردن', run: () => act(() => store.setFlags(id, { is_starred: !t.is_starred }), 'تغییر ناموفق بود.') })
      out.push({ key: 'unread', label: 'علامت‌گذاری به‌عنوان نخوانده', run: () => act(() => store.setFlags(id, { is_read: false }), 'تغییر ناموفق بود.') })
    }
    if (store.canDelete) out.push({ key: 'trash', label: 'انتقال به سطل زباله', danger: true, run: () => act(() => store.move(id, 'trash'), 'انتقال به سطل زباله ناموفق بود.') })
  }
  return out
})
</script>

<template>
  <div class="mail-page flex h-full min-h-0 flex-col overflow-hidden border-y border-border bg-background md:rounded-md md:border" dir="rtl">
    <p v-if="ready && !store.canRead" class="m-auto p-10 text-sm text-muted-foreground">
      شما به بخش مکاتبات دسترسی ندارید.
    </p>

    <template v-else>
      <!-- page header (hidden while a letter is open on a phone/tablet: the letter has its own bar) -->
      <header v-if="!detailOnly" class="flex items-center justify-between gap-3 border-b px-4 py-3 md:px-5">
        <div class="min-w-0">
          <h1 class="text-base font-semibold md:text-lg">
            مکاتبات سازمانی
          </h1>
          <p class="truncate text-xs text-muted-foreground">
            {{ viewTitle }}<template v-if="ready"> · {{ toPersianDigits(store.total) }} مورد</template>
          </p>
        </div>
        <div class="flex shrink-0 items-center gap-2">
          <Button v-if="canManage" variant="outline" class="hidden h-9 md:inline-flex" @click="unitsOpen = true">
            دسترسی واحدها
          </Button>
          <Button v-if="store.canCreate" class="h-11 px-5 md:h-9" @click="newMail">
            نامهٔ جدید
          </Button>
        </div>
      </header>

      <div class="flex min-h-0 flex-1">
        <!-- folders (desktop) -->
        <nav v-if="!detailOnly" class="hidden w-52 shrink-0 overflow-y-auto border-e bg-muted/20 py-3 lg:block" aria-label="پوشه‌ها">
          <p class="px-4 pb-1 text-xs text-muted-foreground">
            پوشه‌ها
          </p>
          <button
            v-for="f in MAIL_FOLDERS"
            :key="f.id"
            class="flex w-full items-center justify-between border-s-2 px-4 py-2 text-start text-sm hover:bg-muted"
            :class="store.view.kind === 'folder' && store.view.folder === f.id ? 'border-primary bg-muted font-medium' : 'border-transparent'"
            @click="store.setView({ kind: 'folder', folder: f.id })"
          >
            <span>{{ f.label }}</span>
            <span v-if="store.folderBadge(f.id)" class="text-xs tabular-nums text-muted-foreground">{{ toPersianDigits(store.folderBadge(f.id)) }}</span>
          </button>
          <button
            class="flex w-full items-center justify-between border-s-2 px-4 py-2 text-start text-sm hover:bg-muted"
            :class="store.view.kind === 'starred' ? 'border-primary bg-muted font-medium' : 'border-transparent'"
            @click="store.setView({ kind: 'starred' })"
          >
            <span>ستاره‌دار</span>
          </button>
          <p class="mt-4 px-4 pb-1 text-xs text-muted-foreground">
            برچسب‌ها
          </p>
          <button
            v-for="l in MAIL_LABELS"
            :key="l.id"
            class="flex w-full items-center justify-between border-s-2 px-4 py-2 text-start text-sm hover:bg-muted"
            :class="store.view.kind === 'label' && store.view.label === l.id ? 'border-primary bg-muted font-medium' : 'border-transparent'"
            @click="store.setView({ kind: 'label', label: l.id })"
          >
            <span :class="l.color">{{ l.label }}</span>
            <span v-if="store.counters.labels[l.id]" class="text-xs tabular-nums text-muted-foreground">{{ toPersianDigits(store.counters.labels[l.id]!) }}</span>
          </button>
        </nav>

        <!-- ============ correspondence list ============ -->
        <section
          v-if="!detailOnly"
          class="flex min-w-0 flex-1 flex-col"
          :class="splitView && 'max-w-[26rem] flex-none basis-[26rem] border-e'"
        >
          <div class="space-y-2 border-b px-4 py-3">
            <select v-model="viewKey" :class="[selectClass, 'lg:hidden']" aria-label="پوشه">
              <optgroup label="پوشه‌ها">
                <option v-for="f in MAIL_FOLDERS" :key="f.id" :value="`folder:${f.id}`">
                  {{ f.label }}{{ store.folderBadge(f.id) ? ` (${toPersianDigits(store.folderBadge(f.id))})` : '' }}
                </option>
                <option value="starred">
                  ستاره‌دار
                </option>
              </optgroup>
              <optgroup label="برچسب‌ها">
                <option v-for="l in MAIL_LABELS" :key="l.id" :value="`label:${l.id}`">
                  {{ l.label }}
                </option>
              </optgroup>
            </select>
            <div class="flex flex-wrap items-center gap-2">
              <Input v-model="store.search" dir="auto" class="h-11 min-w-0 flex-1 basis-48 text-right md:h-9" placeholder="جست‌وجو در موضوع، فرستنده و متن" />
              <select v-model="store.unreadOnly" :class="[selectClass, 'w-auto min-w-28']" aria-label="وضعیت خواندن">
                <option :value="false">
                  همهٔ نامه‌ها
                </option>
                <option :value="true">
                  نخوانده{{ unreadCount ? ` (${toPersianDigits(unreadCount)})` : '' }}
                </option>
              </select>
              <select v-model="store.sort" :class="[selectClass, 'w-auto min-w-28']" aria-label="مرتب‌سازی">
                <option value="newest">
                  جدیدترین
                </option>
                <option value="oldest">
                  قدیمی‌ترین
                </option>
              </select>
            </div>
            <Button v-if="canManage" variant="outline" class="h-11 w-full md:hidden" @click="unitsOpen = true">
              دسترسی واحدها
            </Button>
          </div>

          <div class="min-h-0 flex-1 overflow-y-auto">
            <p v-if="store.error" class="p-6 text-center text-sm text-destructive">
              {{ store.error }}
            </p>
            <p v-else-if="store.loading && !store.rows.length" class="p-6 text-center text-sm text-muted-foreground">
              در حال بارگذاری…
            </p>
            <p v-else-if="!store.rows.length" class="p-10 text-center text-sm text-muted-foreground">
              نامه‌ای در این فهرست وجود ندارد.
            </p>

            <!-- wide table -->
            <table v-else-if="tableMode" class="w-full table-fixed border-collapse text-sm">
              <thead class="sticky top-0 z-10 bg-muted/60 text-xs text-muted-foreground backdrop-blur">
                <tr class="border-b">
                  <th scope="col" class="w-[22%] px-4 py-2 text-start font-medium">
                    {{ folder === 'sent' || folder === 'drafts' ? 'گیرنده' : 'فرستنده' }}
                  </th>
                  <th scope="col" class="px-3 py-2 text-start font-medium">
                    موضوع
                  </th>
                  <th scope="col" class="hidden w-[16%] px-3 py-2 text-start font-medium xl:table-cell">
                    برچسب
                  </th>
                  <th scope="col" class="w-14 px-2 py-2 text-center font-medium">
                    پیوست
                  </th>
                  <th scope="col" class="w-28 px-4 py-2 text-start font-medium">
                    <button class="font-medium hover:text-foreground" @click="store.sort = store.sort === 'newest' ? 'oldest' : 'newest'">
                      تاریخ {{ store.sort === 'newest' ? '↓' : '↑' }}
                    </button>
                  </th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="row in store.rows"
                  :key="row.id"
                  tabindex="0"
                  class="cursor-pointer border-b border-s-[3px] hover:bg-muted/50 focus-visible:bg-muted/50 focus-visible:outline-none"
                  :class="[row.is_read ? 'border-s-transparent' : 'border-s-primary bg-muted/20 font-semibold', store.selectedId === row.id && 'bg-muted']"
                  @click="open(row.id)"
                  @keydown.enter="open(row.id)"
                >
                  <td class="truncate px-4 py-2.5">
                    <span v-if="!row.is_read" class="sr-only">نخوانده — </span>{{ counterparty(row) }}
                  </td>
                  <td class="px-3 py-2.5">
                    <span class="block truncate" dir="auto">{{ row.subject || '(بدون موضوع)' }}<template v-if="row.thread_count > 1"> ({{ toPersianDigits(row.thread_count) }})</template></span>
                    <span class="block truncate text-xs font-normal text-muted-foreground" dir="auto">{{ row.preview }}</span>
                  </td>
                  <td class="hidden px-3 py-2.5 text-xs font-normal xl:table-cell">
                    <span v-for="l in row.labels" :key="l" class="me-1.5 inline-block rounded-sm border px-1.5 py-0.5" :class="labelStyle(l)?.color">{{ labelStyle(l)?.label }}</span>
                  </td>
                  <td class="px-2 py-2.5 text-center text-xs font-normal text-muted-foreground">
                    {{ row.has_attachments ? 'دارد' : '' }}
                  </td>
                  <td class="whitespace-nowrap px-4 py-2.5 text-xs font-normal tabular-nums text-muted-foreground">
                    {{ formatMailDate(row.sent_at || row.created_at) }}
                  </td>
                </tr>
              </tbody>
            </table>

            <!-- compact rows: phone, and the narrow list beside an open letter -->
            <ul v-else class="divide-y">
              <li v-for="row in store.rows" :key="row.id">
                <button
                  class="block min-h-14 w-full border-s-[3px] px-4 py-3 text-start hover:bg-muted/50 focus-visible:bg-muted/50 focus-visible:outline-none"
                  :class="[row.is_read ? 'border-s-transparent' : 'border-s-primary bg-muted/20', store.selectedId === row.id && 'bg-muted']"
                  @click="open(row.id)"
                >
                  <span class="flex items-baseline justify-between gap-3">
                    <span class="min-w-0 truncate text-sm" :class="!row.is_read && 'font-semibold'">
                      <span v-if="!row.is_read" class="sr-only">نخوانده — </span>{{ counterparty(row) }}
                    </span>
                    <span class="shrink-0 text-xs tabular-nums text-muted-foreground">{{ formatMailDate(row.sent_at || row.created_at) }}</span>
                  </span>
                  <span class="mt-0.5 block truncate text-sm" :class="row.is_read ? 'text-foreground/90' : 'font-semibold'" dir="auto">
                    {{ row.subject || '(بدون موضوع)' }}<template v-if="row.thread_count > 1"> ({{ toPersianDigits(row.thread_count) }})</template>
                  </span>
                  <span class="mt-0.5 block truncate text-xs text-muted-foreground" dir="auto">{{ row.preview }}</span>
                  <span v-if="row.labels.length || row.has_attachments || row.is_starred" class="mt-1.5 flex flex-wrap items-center gap-1.5 text-xs text-muted-foreground">
                    <span v-for="l in row.labels" :key="l" class="rounded-sm border px-1.5 py-0.5" :class="labelStyle(l)?.color">{{ labelStyle(l)?.label }}</span>
                    <span v-if="row.has_attachments">دارای پیوست</span>
                    <span v-if="row.is_starred">ستاره‌دار</span>
                  </span>
                </button>
              </li>
            </ul>

            <div v-if="store.hasMore" class="p-3">
              <Button variant="outline" class="h-11 w-full md:h-9" :disabled="store.loading" @click="store.loadMore()">
                نمایش موارد بیشتر
              </Button>
            </div>
          </div>
        </section>

        <!-- ============ letter ============ -->
        <section v-if="splitView || detailOnly" class="flex min-w-0 flex-1 flex-col">
          <p v-if="!store.thread" class="m-auto p-10 text-sm text-muted-foreground">
            {{ store.threadLoading ? 'در حال بارگذاری…' : 'نامه‌ای انتخاب نشده است.' }}
          </p>

          <template v-else>
            <!-- bar: back + operations -->
            <div class="flex flex-wrap items-center gap-2 border-b px-3 py-2 md:px-4">
              <Button v-if="detailOnly" variant="ghost" class="h-11 gap-1 px-3 md:h-9" @click="backToList">
                ← بازگشت به فهرست
              </Button>
              <div class="ms-auto hidden flex-wrap items-center gap-1.5 md:flex">
                <Button v-if="canReply" class="h-9" @click="focusReply">
                  پاسخ
                </Button>
                <Button v-if="canReply && lastMessage && !lastMessage.is_draft" variant="outline" class="h-9" @click="forward(lastMessage)">
                  ارجاع
                </Button>
                <Button v-for="a in threadActions" :key="a.key" variant="outline" class="h-9" :class="a.danger && 'text-destructive'" @click="a.run()">
                  {{ a.label }}
                </Button>
                <DropdownMenu v-if="canLabel">
                  <DropdownMenuTrigger as-child>
                    <Button variant="outline" class="h-9">
                      برچسب‌ها
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end" dir="rtl">
                    <DropdownMenuCheckboxItem
                      v-for="l in MAIL_LABELS"
                      :key="l.id"
                      :model-value="store.thread.labels.includes(l.id)"
                      @select.prevent="toggleLabel(l.id)"
                    >
                      {{ l.label }}
                    </DropdownMenuCheckboxItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </div>
            </div>

            <div class="min-h-0 flex-1 overflow-y-auto px-4 py-5 md:px-6">
              <h2 class="text-lg font-semibold leading-8" dir="auto">
                {{ store.thread.subject || '(بدون موضوع)' }}
              </h2>
              <p v-if="store.thread.labels.length" class="mt-1 flex flex-wrap gap-1.5 text-xs">
                <span v-for="l in store.thread.labels" :key="l" class="rounded-sm border px-1.5 py-0.5" :class="labelStyle(l)?.color">{{ labelStyle(l)?.label }}</span>
              </p>

              <button v-if="hiddenCount > 0" class="mt-4 text-sm text-primary hover:underline" @click="showAllMessages = true">
                نمایش {{ toPersianDigits(hiddenCount) }} نامهٔ قبلی این مکاتبه
              </button>

              <article v-for="m in visibleMessages" :key="m.id" class="mt-5 border">
                <header class="border-b bg-muted/30 p-4">
                  <div class="flex items-start gap-3">
                    <MailPersonAvatar :person="store.person(m.sender_id)" size="size-9" />
                    <dl class="grid min-w-0 flex-1 grid-cols-[4rem_minmax(0,1fr)] gap-x-3 gap-y-1.5 text-sm">
                      <dt class="text-muted-foreground">
                        فرستنده
                      </dt>
                      <dd class="min-w-0">
                        <span class="font-medium">{{ nameOf(m.sender_id) }}</span>
                        <span v-if="store.person(m.sender_id)?.department" class="text-muted-foreground"> · {{ store.person(m.sender_id)?.department }}</span>
                        <span class="block truncate text-xs text-muted-foreground" dir="ltr">{{ store.person(m.sender_id)?.email }}</span>
                      </dd>
                      <dt class="text-muted-foreground">
                        گیرنده
                      </dt>
                      <dd class="min-w-0 break-words">
                        {{ namesOf(m.to) || '—' }}
                      </dd>
                      <template v-if="m.cc.length">
                        <dt class="text-muted-foreground">
                          رونوشت
                        </dt>
                        <dd class="min-w-0 break-words">
                          {{ namesOf(m.cc) }}
                        </dd>
                      </template>
                      <dt class="text-muted-foreground">
                        تاریخ
                      </dt>
                      <dd class="tabular-nums">
                        {{ m.is_draft ? 'پیش‌نویس (ارسال نشده)' : formatMailDateLong(m.sent_at || m.created_at) }}
                      </dd>
                    </dl>
                  </div>
                </header>
                <div class="whitespace-pre-wrap break-words p-4 text-[15px] leading-8" dir="auto">
                  {{ m.body }}
                </div>
                <div v-if="m.attachments.length" class="border-t p-4">
                  <p class="mb-2 text-xs text-muted-foreground">
                    پیوست‌ها ({{ toPersianDigits(m.attachments.length) }})
                  </p>
                  <ul class="divide-y rounded-md border">
                    <li v-for="f in m.attachments" :key="f.id" class="flex min-h-11 items-center gap-3 px-3 py-2 text-sm">
                      <span class="min-w-0 flex-1 truncate" dir="auto">{{ f.name }}</span>
                      <span class="shrink-0 text-xs tabular-nums text-muted-foreground">{{ formatFileSize(f.size) }}</span>
                      <button class="shrink-0 px-2 py-1.5 text-primary hover:underline" @click="act(() => store.downloadFile(f), 'دانلود فایل ناموفق بود.')">
                        دانلود
                      </button>
                    </li>
                  </ul>
                </div>
              </article>

              <!-- reply -->
              <div v-if="canReply" ref="replyBox" class="mt-6 scroll-mb-24 border">
                <p class="border-b bg-muted/30 px-4 py-2 text-sm font-medium">
                  پاسخ به {{ nameOf(lastMessage!.is_mine ? (lastMessage!.to[0] ?? 0) : lastMessage!.sender_id) }}
                </p>
                <Textarea v-model="replyBody" dir="auto" rows="5" class="min-h-32 resize-y rounded-none border-0 text-right shadow-none focus-visible:ring-0" placeholder="متن پاسخ را بنویسید" />
                <ul v-if="replyFiles.length" class="divide-y border-t">
                  <li v-for="f in replyFiles" :key="f.id" class="flex min-h-11 items-center gap-3 px-4 py-2 text-sm">
                    <span class="min-w-0 flex-1 truncate" dir="auto">{{ f.name }}</span>
                    <button class="shrink-0 px-2 py-1.5 text-destructive hover:underline" @click="replyFiles = replyFiles.filter(x => x.id !== f.id); store.removeUpload(f.id)">
                      حذف
                    </button>
                  </li>
                </ul>
                <div class="flex flex-wrap items-center gap-x-5 gap-y-2 border-t bg-muted/30 px-4 py-3">
                  <input ref="replyInput" type="file" multiple class="hidden" @change="pickReplyFiles">
                  <Button variant="outline" class="h-11 md:h-9" :disabled="replyUploading" @click="replyInput?.click()">
                    {{ replyUploading ? 'در حال بارگذاری…' : 'پیوست فایل' }}
                  </Button>
                  <label class="flex min-h-11 cursor-pointer items-center gap-2 text-sm md:min-h-0">
                    <input v-model="replyAll" type="checkbox" class="size-4"> پاسخ به همه
                  </label>
                  <label v-if="store.canUpdate" class="flex min-h-11 cursor-pointer items-center gap-2 text-sm md:min-h-0">
                    <input
                      type="checkbox"
                      class="size-4"
                      :checked="store.thread.is_muted"
                      @change="act(() => store.setFlags(store.selectedId!, { is_muted: ($event.target as HTMLInputElement).checked }), 'تغییر ناموفق بود.')"
                    > بی‌صدا کردن گفتگو
                  </label>
                  <Button class="ms-auto h-11 px-6 md:h-9" :disabled="replySending || replyUploading || (!replyBody.trim() && !replyFiles.length)" @click="sendReply">
                    ارسال پاسخ
                  </Button>
                </div>
              </div>
            </div>

            <!-- phone/tablet action bar: the main operations stay under the thumb -->
            <div class="flex items-center gap-2 border-t bg-background px-3 pt-2 pb-[max(0.5rem,env(safe-area-inset-bottom))] md:hidden">
              <Button v-if="canReply" class="h-11 flex-1" @click="focusReply">
                پاسخ
              </Button>
              <Button v-if="canReply && lastMessage && !lastMessage.is_draft" variant="outline" class="h-11 flex-1" @click="forward(lastMessage)">
                ارجاع
              </Button>
              <DropdownMenu v-if="threadActions.length || canLabel">
                <DropdownMenuTrigger as-child>
                  <Button variant="outline" class="h-11 flex-1">
                    بیشتر
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" dir="rtl" class="min-w-56">
                  <DropdownMenuItem v-for="a in threadActions" :key="a.key" class="min-h-11 text-base" :class="a.danger && 'text-destructive'" @select="a.run()">
                    {{ a.label }}
                  </DropdownMenuItem>
                  <template v-if="canLabel">
                    <DropdownMenuSeparator v-if="threadActions.length" />
                    <DropdownMenuLabel class="text-xs text-muted-foreground">
                      برچسب‌ها
                    </DropdownMenuLabel>
                    <DropdownMenuCheckboxItem
                      v-for="l in MAIL_LABELS"
                      :key="l.id"
                      class="min-h-11 text-base"
                      :model-value="store.thread.labels.includes(l.id)"
                      @select.prevent="toggleLabel(l.id)"
                    >
                      {{ l.label }}
                    </DropdownMenuCheckboxItem>
                  </template>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
          </template>
        </section>

        <!-- wide screen, nothing selected: the list takes the full width, no placeholder pane needed -->
      </div>
    </template>

    <MailComposeDialog v-model:open="composeOpen" :init="composeInit" />
    <MailUnitAccessDialog v-model:open="unitsOpen" />
  </div>
</template>
