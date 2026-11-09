<script setup lang="ts">
type Folder = 'inbox' | 'sent' | 'drafts' | 'archive' | 'trash'

interface MailItem {
  id: number
  sender: string
  email: string
  subject: string
  preview: string
  body: string
  time: string
  folder: Folder
  unread: boolean
  starred: boolean
  tag?: string
}

const folders: { id: Folder; label: string; icon: string }[] = [
  { id: 'inbox', label: 'Inbox', icon: 'lucide:inbox' },
  { id: 'sent', label: 'Sent', icon: 'lucide:send' },
  { id: 'drafts', label: 'Drafts', icon: 'lucide:file-edit' },
  { id: 'archive', label: 'Archive', icon: 'lucide:archive' },
  { id: 'trash', label: 'Trash', icon: 'lucide:trash-2' },
]

const mails = ref<MailItem[]>([
  {
    id: 1,
    sender: 'Sara Ahmadi',
    email: 'sara@polychem.co',
    subject: 'Q3 sales report is ready',
    preview: 'I have attached the final sales report for your review...',
    body: 'Hi team,\n\nThe final Q3 sales report is ready for review. The dashboard has also been updated with the latest numbers and regional breakdowns.\n\nPlease send your notes before Thursday so we can prepare the management summary.\n\nBest,\nSara',
    time: '09:42',
    folder: 'inbox',
    unread: true,
    starred: true,
    tag: 'Sales',
  },
  {
    id: 2,
    sender: 'Arman Karimi',
    email: 'arman@polychem.co',
    subject: 'Warehouse delivery update',
    preview: 'The inbound shipment has arrived at the central warehouse...',
    body: 'Hello,\n\nThe inbound shipment arrived at the central warehouse this morning. The receiving team is checking quantities now and will update the inventory records shortly.\n\nRegards,\nArman',
    time: 'Yesterday',
    folder: 'inbox',
    unread: true,
    starred: false,
    tag: 'Warehouse',
  },
  {
    id: 3,
    sender: 'Niloofar Hosseini',
    email: 'niloofar@polychem.co',
    subject: 'Customer meeting notes',
    preview: 'Here are the action items from our meeting with Atlas...',
    body: 'Hi,\n\nHere are the action items from our meeting with Atlas Industries. I have assigned the follow-ups in the task workspace.\n\nThanks,\nNiloofar',
    time: 'Mon',
    folder: 'inbox',
    unread: false,
    starred: false,
  },
  {
    id: 4,
    sender: 'Finance team',
    email: 'finance@polychem.co',
    subject: 'Invoice approval needed',
    preview: 'Two supplier invoices are waiting for your approval...',
    body: 'Hello,\n\nTwo supplier invoices are waiting for your approval in Finance. Please review them before the payment run.\n\nFinance team',
    time: 'Sun',
    folder: 'inbox',
    unread: false,
    starred: true,
    tag: 'Action required',
  },
  {
    id: 5,
    sender: 'You',
    email: 'you@polychem.co',
    subject: 'Re: Brand guidelines',
    preview: 'Thanks, I will review the latest version today...',
    body: 'Thanks, I will review the latest version today and share feedback with the team.',
    time: 'Fri',
    folder: 'sent',
    unread: false,
    starred: false,
  },
])

const activeFolder = ref<Folder>('inbox')
const activeMailId = ref(1)
const search = ref('')
const showCompose = ref(false)
const composeMinimized = ref(false)
const composeFullscreen = ref(false)
const composeTo = ref('')
const composeCc = ref('')
const composeBcc = ref('')
const composeSubject = ref('')
const composeBody = ref('')
const showCc = ref(false)
const showBcc = ref(false)
const composeAttachments = ref<File[]>([])
const attachmentInput = ref<HTMLInputElement | null>(null)
const composeEditor = ref<HTMLDivElement | null>(null)

const visibleMails = computed(() => {
  const query = search.value.trim().toLowerCase()
  return mails.value.filter((mail) => {
    const inFolder = mail.folder === activeFolder.value
    const matches = !query || [mail.sender, mail.subject, mail.preview].some(value => value.toLowerCase().includes(query))
    return inFolder && matches
  })
})

const activeMail = computed(() => mails.value.find(mail => mail.id === activeMailId.value) ?? null)
const unreadCount = computed(() => mails.value.filter(mail => mail.folder === 'inbox' && mail.unread).length)

function selectFolder(folder: Folder) {
  activeFolder.value = folder
  const firstMail = mails.value.find(mail => mail.folder === folder)
  if (firstMail) activeMailId.value = firstMail.id
}

function openMail(mail: MailItem) {
  activeMailId.value = mail.id
  mail.unread = false
}

function toggleStar(mail: MailItem) {
  mail.starred = !mail.starred
}

function sendMail() {
  if (!composeTo.value.trim() || !composeSubject.value.trim()) return
  showCompose.value = false
  composeMinimized.value = false
  composeFullscreen.value = false
  composeTo.value = ''
  composeCc.value = ''
  composeBcc.value = ''
  composeSubject.value = ''
  composeBody.value = ''
  composeAttachments.value = []
  showCc.value = false
  showBcc.value = false
}

function openCompose() {
  showCompose.value = true
  composeMinimized.value = false
}

function onBodyInput(event: Event) {
  composeBody.value = (event.target as HTMLDivElement).innerHTML
}

function formatBody(command: string, value?: string) {
  composeEditor.value?.focus()
  document.execCommand(command, false, value)
  if (composeEditor.value) composeBody.value = composeEditor.value.innerHTML
}

function addLink() {
  const url = window.prompt('Enter URL')
  if (url) formatBody('createLink', url)
}

function onAttachments(event: Event) {
  const files = (event.target as HTMLInputElement).files
  if (files) composeAttachments.value.push(...Array.from(files))
  if (attachmentInput.value) attachmentInput.value.value = ''
}

function removeAttachment(index: number) {
  composeAttachments.value.splice(index, 1)
}

function folderCount(folder: Folder) {
  return mails.value.filter(mail => mail.folder === folder && mail.unread).length
}
</script>

<template>
  <div class="mail-page flex h-full min-h-0 flex-col overflow-hidden rounded-lg border border-border bg-card shadow-sm">
    <div class="flex min-h-0 flex-1">
      <aside class="hidden w-60 shrink-0 flex-col border-e border-border bg-muted/30 p-4 lg:flex">
        <div class="mb-5 flex items-center gap-2 px-2">
          <div class="flex size-8 items-center justify-center rounded-md bg-primary text-primary-foreground">
            <Icon name="lucide:mail" class="size-4" />
          </div>
          <div>
            <p class="text-sm font-semibold text-foreground">Mail platform</p>
            <p class="text-[11px] text-muted-foreground">Polychem workspace</p>
          </div>
        </div>

        <button class="mb-5 flex h-9 items-center justify-center gap-2 rounded-md bg-primary px-3 text-sm font-medium text-primary-foreground transition-opacity hover:opacity-90" @click="openCompose">
          <Icon name="lucide:pen-line" class="size-4" />
          Compose email
        </button>

        <p class="mb-2 px-2 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">Mailbox</p>
        <nav class="space-y-1">
          <button
            v-for="folder in folders"
            :key="folder.id"
            class="flex h-9 w-full items-center gap-3 rounded-md px-2.5 text-sm transition-colors"
            :class="activeFolder === folder.id ? 'bg-primary/15 font-medium text-foreground' : 'text-muted-foreground hover:bg-accent hover:text-foreground'"
            @click="selectFolder(folder.id)"
          >
            <Icon :name="folder.icon" class="size-4" />
            <span>{{ folder.label }}</span>
            <span v-if="folderCount(folder.id)" class="ms-auto rounded-full bg-primary px-1.5 text-[10px] font-semibold text-primary-foreground">{{ folderCount(folder.id) }}</span>
          </button>
        </nav>

        <div class="mt-auto rounded-md border border-border bg-card p-3">
          <div class="mb-2 flex items-center gap-2">
            <div class="flex size-7 items-center justify-center rounded-full bg-foreground text-[11px] font-semibold text-background">YM</div>
            <div class="min-w-0">
              <p class="truncate text-xs font-medium text-foreground">You</p>
              <p class="truncate text-[10px] text-muted-foreground">you@polychem.co</p>
            </div>
          </div>
          <p class="text-[10px] text-muted-foreground">{{ unreadCount }} unread messages</p>
        </div>
      </aside>

      <section class="flex min-w-0 flex-1 flex-col border-e border-border lg:max-w-[390px]">
        <div class="flex items-center gap-3 border-b border-border px-4 py-3">
          <div class="relative min-w-0 flex-1">
            <Icon name="lucide:search" class="absolute start-2.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
            <input v-model="search" class="h-9 w-full rounded-md border border-input bg-background ps-9 pe-3 text-sm text-foreground outline-none ring-ring placeholder:text-muted-foreground focus:ring-2" placeholder="Search emails...">
          </div>
          <button class="flex size-9 shrink-0 items-center justify-center rounded-md border border-input text-muted-foreground hover:bg-accent hover:text-foreground lg:hidden" title="Compose" @click="openCompose">
            <Icon name="lucide:pen-line" class="size-4" />
          </button>
        </div>
        <div class="flex items-center justify-between border-b border-border px-4 py-3">
          <div>
            <h1 class="text-sm font-semibold text-foreground">{{ folders.find(folder => folder.id === activeFolder)?.label }}</h1>
            <p class="text-[11px] text-muted-foreground">{{ visibleMails.length }} conversations</p>
          </div>
          <button class="flex size-8 items-center justify-center rounded-md text-muted-foreground hover:bg-accent hover:text-foreground" title="Refresh">
            <Icon name="lucide:refresh-cw" class="size-4" />
          </button>
        </div>
        <div class="min-h-0 flex-1 overflow-y-auto">
          <button
            v-for="mail in visibleMails"
            :key="mail.id"
            class="group w-full border-b border-border px-4 py-3 text-start transition-colors hover:bg-accent/60"
            :class="activeMailId === mail.id ? 'bg-primary/10' : ''"
            @click="openMail(mail)"
          >
            <div class="flex items-start gap-3">
              <div class="flex size-8 shrink-0 items-center justify-center rounded-full bg-secondary text-[10px] font-semibold text-secondary-foreground">{{ mail.sender.split(' ').map(part => part[0]).join('').slice(0, 2) }}</div>
              <div class="min-w-0 flex-1">
                <div class="flex items-center gap-2">
                  <span class="truncate text-xs" :class="mail.unread ? 'font-semibold text-foreground' : 'text-muted-foreground'">{{ mail.sender }}</span>
                  <span class="ms-auto shrink-0 text-[10px] text-muted-foreground">{{ mail.time }}</span>
                </div>
                <p class="mt-1 truncate text-sm" :class="mail.unread ? 'font-semibold text-foreground' : 'text-foreground/80'">{{ mail.subject }}</p>
                <p class="mt-1 truncate text-xs text-muted-foreground">{{ mail.preview }}</p>
                <span v-if="mail.tag" class="mt-2 inline-flex rounded bg-primary/15 px-1.5 py-0.5 text-[10px] font-medium text-foreground">{{ mail.tag }}</span>
              </div>
              <button class="shrink-0 text-muted-foreground hover:text-primary" @click.stop="toggleStar(mail)">
                <Icon :name="mail.starred ? 'lucide:star' : 'lucide:star'" class="size-3.5" :class="mail.starred ? 'fill-primary text-primary' : ''" />
              </button>
            </div>
          </button>
          <div v-if="visibleMails.length === 0" class="flex h-48 flex-col items-center justify-center gap-2 px-5 text-center">
            <Icon name="lucide:search-x" class="size-8 text-muted-foreground/50" />
            <p class="text-sm font-medium text-foreground">No emails found</p>
            <p class="text-xs text-muted-foreground">Try another search or folder.</p>
          </div>
        </div>
      </section>

      <section class="hidden min-w-0 flex-1 flex-col md:flex">
        <template v-if="activeMail">
          <header class="flex items-center gap-3 border-b border-border px-6 py-4">
            <div class="min-w-0 flex-1">
              <h2 class="truncate text-base font-semibold text-foreground">{{ activeMail.subject }}</h2>
              <p class="mt-1 text-xs text-muted-foreground">Inbox / {{ activeMail.sender }}</p>
            </div>
            <button class="flex size-8 items-center justify-center rounded-md text-muted-foreground hover:bg-accent hover:text-foreground" title="More actions">
              <Icon name="lucide:more-horizontal" class="size-4" />
            </button>
          </header>
          <div class="min-h-0 flex-1 overflow-y-auto px-6 py-6">
            <div class="mb-6 flex items-start gap-3">
              <div class="flex size-10 shrink-0 items-center justify-center rounded-full bg-primary text-xs font-semibold text-primary-foreground">{{ activeMail.sender.split(' ').map(part => part[0]).join('').slice(0, 2) }}</div>
              <div>
                <p class="text-sm font-semibold text-foreground">{{ activeMail.sender }}</p>
                <p class="text-xs text-muted-foreground">{{ activeMail.email }} · {{ activeMail.time }}</p>
              </div>
            </div>
            <div class="whitespace-pre-line text-sm leading-7 text-foreground/80">{{ activeMail.body }}</div>
            <div class="mt-8 flex items-center gap-2 border-t border-border pt-5">
              <button class="inline-flex h-8 items-center gap-2 rounded-md border border-input px-3 text-xs font-medium text-foreground hover:bg-accent" @click="openCompose">
                <Icon name="lucide:reply" class="size-3.5" /> Reply
              </button>
              <button class="inline-flex h-8 items-center gap-2 rounded-md border border-input px-3 text-xs font-medium text-foreground hover:bg-accent">
                <Icon name="lucide:forward" class="size-3.5" /> Forward
              </button>
            </div>
          </div>
        </template>
      </section>
    </div>

    <div v-if="showCompose" class="fixed inset-0 z-50 flex items-end justify-center bg-foreground/20 p-4 sm:items-center" @click.self="showCompose = false">
      <form
        class="flex w-full flex-col overflow-hidden rounded-lg border border-border bg-card shadow-xl transition-[height,max-width] duration-200"
        :class="composeFullscreen ? 'h-[calc(100vh-2rem)] max-w-6xl' : composeMinimized ? 'h-12 max-w-lg' : 'h-[min(720px,calc(100vh-2rem))] max-w-2xl'"
        @submit.prevent="sendMail"
      >
        <div class="flex shrink-0 items-center justify-between border-b border-border bg-foreground px-4 py-3 text-background">
          <p class="text-sm font-medium">New message</p>
          <div class="flex items-center gap-1">
            <button type="button" class="rounded p-1.5 text-background/70 hover:bg-background/10 hover:text-background" :title="composeMinimized ? 'Restore' : 'Minimize'" @click="composeMinimized = !composeMinimized">
              <Icon :name="composeMinimized ? 'lucide:chevron-up' : 'lucide:minus'" class="size-4" />
            </button>
            <button type="button" class="rounded p-1.5 text-background/70 hover:bg-background/10 hover:text-background" :title="composeFullscreen ? 'Exit full screen' : 'Full screen'" @click="composeFullscreen = !composeFullscreen; composeMinimized = false">
              <Icon :name="composeFullscreen ? 'lucide:panels-top-left' : 'lucide:maximize-2'" class="size-4" />
            </button>
            <button type="button" class="rounded p-1.5 text-background/70 hover:bg-background/10 hover:text-background" title="Close" @click="showCompose = false"><Icon name="lucide:x" class="size-4" /></button>
          </div>
        </div>

        <template v-if="!composeMinimized">
          <div class="shrink-0 space-y-1 px-4 pt-3">
            <div class="flex items-center border-b border-border">
              <label class="w-12 shrink-0 text-xs text-muted-foreground" for="compose-to">To</label>
              <input id="compose-to" v-model="composeTo" required class="h-9 min-w-0 flex-1 bg-transparent text-sm text-foreground outline-none" placeholder="recipient@company.com">
              <button type="button" class="px-1 text-[11px] text-muted-foreground hover:text-foreground" @click="showCc = !showCc">Cc</button>
              <button type="button" class="px-1 text-[11px] text-muted-foreground hover:text-foreground" @click="showBcc = !showBcc">Bcc</button>
            </div>
            <div v-if="showCc" class="flex items-center border-b border-border">
              <label class="w-12 shrink-0 text-xs text-muted-foreground" for="compose-cc">Cc</label>
              <input id="compose-cc" v-model="composeCc" class="h-9 min-w-0 flex-1 bg-transparent text-sm text-foreground outline-none" placeholder="copy@company.com">
            </div>
            <div v-if="showBcc" class="flex items-center border-b border-border">
              <label class="w-12 shrink-0 text-xs text-muted-foreground" for="compose-bcc">Bcc</label>
              <input id="compose-bcc" v-model="composeBcc" class="h-9 min-w-0 flex-1 bg-transparent text-sm text-foreground outline-none" placeholder="hidden@company.com">
            </div>
            <input v-model="composeSubject" required class="h-10 w-full border-b border-border bg-transparent px-0 text-sm font-medium text-foreground outline-none placeholder:font-normal focus:border-primary" placeholder="Subject">
          </div>

          <div class="flex flex-wrap items-center gap-0.5 border-b border-border px-4 py-2">
            <button v-for="tool in [
              { icon: 'lucide:bold', command: 'bold', label: 'Bold' },
              { icon: 'lucide:italic', command: 'italic', label: 'Italic' },
              { icon: 'lucide:underline', command: 'underline', label: 'Underline' },
            ]" :key="tool.command" type="button" class="flex size-7 items-center justify-center rounded text-muted-foreground hover:bg-accent hover:text-foreground" :title="tool.label" @click="formatBody(tool.command)">
              <Icon :name="tool.icon" class="size-3.5" />
            </button>
            <span class="mx-1 h-5 w-px bg-border" />
            <button v-for="alignment in [
              { icon: 'lucide:align-left', command: 'justifyLeft', label: 'Align left' },
              { icon: 'lucide:align-center', command: 'justifyCenter', label: 'Align center' },
              { icon: 'lucide:align-right', command: 'justifyRight', label: 'Align right' },
              { icon: 'lucide:align-justify', command: 'justifyFull', label: 'Justify' },
            ]" :key="alignment.command" type="button" class="flex size-7 items-center justify-center rounded text-muted-foreground hover:bg-accent hover:text-foreground" :title="alignment.label" @click="formatBody(alignment.command)">
              <Icon :name="alignment.icon" class="size-3.5" />
            </button>
            <span class="mx-1 h-5 w-px bg-border" />
            <button type="button" class="flex size-7 items-center justify-center rounded text-muted-foreground hover:bg-accent hover:text-foreground" title="Bullet list" @click="formatBody('insertUnorderedList')"><Icon name="lucide:list" class="size-3.5" /></button>
            <button type="button" class="flex size-7 items-center justify-center rounded text-muted-foreground hover:bg-accent hover:text-foreground" title="Numbered list" @click="formatBody('insertOrderedList')"><Icon name="lucide:list-ordered" class="size-3.5" /></button>
            <button type="button" class="flex size-7 items-center justify-center rounded text-muted-foreground hover:bg-accent hover:text-foreground" title="Add link" @click="addLink"><Icon name="lucide:link" class="size-3.5" /></button>
          </div>

          <div ref="composeEditor" contenteditable="true" class="min-h-0 flex-1 overflow-y-auto px-4 py-4 text-sm leading-7 text-foreground outline-none empty:before:text-muted-foreground empty:before:content-['Write_your_message...']" @input="onBodyInput" />

          <div v-if="composeAttachments.length" class="flex flex-wrap gap-2 border-t border-border px-4 py-2">
            <div v-for="(file, index) in composeAttachments" :key="`${file.name}-${index}`" class="flex max-w-full items-center gap-2 rounded border border-border bg-muted/40 px-2 py-1 text-xs text-foreground">
              <Icon name="lucide:paperclip" class="size-3.5 shrink-0 text-muted-foreground" />
              <span class="max-w-48 truncate">{{ file.name }}</span>
              <button type="button" class="text-muted-foreground hover:text-destructive" title="Remove attachment" @click="removeAttachment(index)"><Icon name="lucide:x" class="size-3" /></button>
            </div>
          </div>

          <div class="flex shrink-0 items-center gap-2 border-t border-border px-4 py-3">
            <button type="submit" class="inline-flex h-9 items-center gap-2 rounded-md bg-primary px-4 text-xs font-medium text-primary-foreground hover:opacity-90"><Icon name="lucide:send" class="size-3.5" /> Send email</button>
            <input ref="attachmentInput" type="file" multiple class="hidden" @change="onAttachments">
            <button type="button" class="flex size-9 items-center justify-center rounded-md text-muted-foreground hover:bg-accent hover:text-foreground" title="Attach files" @click="attachmentInput?.click()"><Icon name="lucide:paperclip" class="size-4" /></button>
            <span class="ms-auto text-[11px] text-muted-foreground">{{ composeAttachments.length }} attachment{{ composeAttachments.length === 1 ? '' : 's' }}</span>
            <button type="button" class="flex size-9 items-center justify-center rounded-md text-muted-foreground hover:bg-accent hover:text-destructive" title="Discard" @click="showCompose = false"><Icon name="lucide:trash-2" class="size-4" /></button>
          </div>
        </template>
      </form>
    </div>
  </div>
</template>