// Correspondence (مکاتبات) store. The backend (/api/mail) enforces every permission; `meta.access`
// only decides which controls are shown.
import { ApiError, apiFetch, apiFetchBlob } from '~/services/backendApi'
import type { MailFile, MailFolder, MailLabel, MailMessage, MailMeta, MailPerson, MailRow, MailThread } from '~/utils/mail'

export interface ComposePayload {
  to: number[]
  cc: number[]
  subject: string
  body: string
  attachment_ids: string[]
  parent_id?: number | null
}
type View = { kind: 'folder', folder: MailFolder } | { kind: 'label', label: MailLabel } | { kind: 'starred' }

export const useMailStore = defineStore('mail', {
  state: () => ({
    meta: null as MailMeta | null,
    view: { kind: 'folder', folder: 'inbox' } as View,
    search: '',
    unreadOnly: false,
    sort: 'newest' as 'newest' | 'oldest',
    rows: [] as MailRow[],
    total: 0,
    page: 1,
    loading: false,
    error: '',
    people: {} as Record<number, MailPerson>,
    counters: { folders: {} as Record<string, { total: number, unread: number }>, labels: {} as Record<string, number> },
    thread: null as MailThread | null,
    selectedId: null as number | null,
    threadLoading: false,
  }),
  getters: {
    canRead: s => !!s.meta?.access.read,
    canCreate: s => !!s.meta?.access.create,
    canUpdate: s => !!s.meta?.access.update,
    canDelete: s => !!s.meta?.access.delete,
    person: s => (id: number): MailPerson | undefined => s.people[id],
    folderBadge: s => (f: MailFolder) => {
      const c = s.counters.folders[f]
      if (!c) return 0
      return f === 'inbox' ? c.unread : c.total
    },
    hasMore: s => s.rows.length < s.total,
  },
  actions: {
    mergePeople(p: Record<string, MailPerson> | undefined) {
      for (const [k, v] of Object.entries(p || {})) this.people[Number(k)] = v
    },
    async loadMeta() {
      this.meta = await apiFetch<MailMeta>('/mail/meta')
    },
    async refreshCounters() {
      try { this.counters = await apiFetch('/mail/counters') }
      catch { /* the sidebar numbers are cosmetic */ }
    },
    async loadList(reset = true) {
      if (reset) { this.page = 1; this.rows = [] }
      this.loading = true
      this.error = ''
      try {
        const query: Record<string, string | number | boolean | undefined> = {
          q: this.search.trim() || undefined, unread: this.unreadOnly || undefined, sort: this.sort,
          page: this.page, per_page: 30,
        }
        if (this.view.kind === 'folder') query.folder = this.view.folder
        else if (this.view.kind === 'label') query.label = this.view.label
        else query.starred = true
        const res = await apiFetch<{ items: MailRow[], people: Record<string, MailPerson>, total: number }>('/mail/threads', { query })
        this.mergePeople(res.people)
        this.rows = reset ? res.items : [...this.rows, ...res.items]
        this.total = res.total
      }
      catch (e) {
        this.error = e instanceof ApiError ? e.message : 'بارگذاری مکاتبات ناموفق بود.'
      }
      finally { this.loading = false }
    },
    async loadMore() {
      if (!this.hasMore || this.loading) return
      this.page += 1
      await this.loadList(false)
    },
    async setView(v: View) {
      this.view = v
      this.thread = null
      this.selectedId = null
      await this.loadList()
    },
    async openThread(messageId: number) {
      this.selectedId = messageId
      this.threadLoading = true
      try {
        const t = await apiFetch<MailThread>(`/mail/messages/${messageId}/thread`)
        this.mergePeople(t.people)
        this.thread = t
        const row = this.rows.find(r => r.id === messageId)
        if (row && !row.is_read && this.canUpdate) {
          await this.setFlags(messageId, { is_read: true })
        }
      }
      finally { this.threadLoading = false }
    },
    async setFlags(id: number, flags: { is_read?: boolean, is_starred?: boolean, is_muted?: boolean }) {
      const t = await apiFetch<MailThread>(`/mail/messages/${id}/flags`, { method: 'PATCH', body: flags })
      this.applyThread(id, t)
    },
    async setLabels(id: number, labels: MailLabel[]) {
      this.applyThread(id, await apiFetch<MailThread>(`/mail/messages/${id}/labels`, { method: 'PUT', body: { labels } }))
    },
    applyThread(id: number, t: MailThread) {
      this.mergePeople(t.people)
      if (this.selectedId === id) this.thread = t
      const row = this.rows.find(r => r.id === id)
      if (row) {
        row.is_read = t.messages.every(m => m.is_read)
        row.is_starred = t.is_starred
        row.labels = t.labels
      }
      this.refreshCounters()
    },
    async move(id: number, folder: 'inbox' | 'archive' | 'spam' | 'trash') {
      await apiFetch(`/mail/messages/${id}/move`, { method: 'POST', body: { folder } })
      await this.afterRemoval(id)
    },
    async deletePermanently(id: number) {
      await apiFetch(`/mail/messages/${id}`, { method: 'DELETE' })
      await this.afterRemoval(id)
    },
    async afterRemoval(id: number) {
      this.rows = this.rows.filter(r => r.id !== id)
      this.total = Math.max(0, this.total - 1)
      if (this.selectedId === id) { this.selectedId = null; this.thread = null }
      this.refreshCounters()
    },
    async searchPeople(q: string, exclude: number[]): Promise<MailPerson[]> {
      return apiFetch<MailPerson[]>('/mail/recipients', { query: { q, limit: 20, exclude: exclude.join(',') || undefined } })
    },
    async uploadFile(file: File): Promise<MailFile> {
      const fd = new FormData()
      fd.append('file', file)
      return apiFetch<MailFile>('/mail/attachments', { method: 'POST', body: fd })
    },
    async removeUpload(id: string) {
      try { await apiFetch(`/mail/attachments/${id}`, { method: 'DELETE' }) }
      catch { /* an already-removed upload is fine */ }
    },
    async downloadFile(f: MailFile) {
      const blob = await apiFetchBlob(`/mail/attachments/${f.id}`)
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = f.name
      document.body.appendChild(a)
      a.click()
      a.remove()
      URL.revokeObjectURL(url)
    },
    async send(p: ComposePayload, draftId: number | null): Promise<MailMessage> {
      const res = draftId
        ? await apiFetch<{ message: MailMessage, people: Record<string, MailPerson> }>(`/mail/drafts/${draftId}/send`, { method: 'POST', body: p })
        : await apiFetch<{ message: MailMessage, people: Record<string, MailPerson> }>('/mail/messages', { method: 'POST', body: p })
      this.mergePeople(res.people)
      await Promise.all([this.loadList(), this.refreshCounters()])
      return res.message
    },
    async reply(id: number, body: { body: string, reply_all: boolean, attachment_ids: string[] }) {
      const res = await apiFetch<{ message: MailMessage, people: Record<string, MailPerson> }>(`/mail/messages/${id}/reply`, { method: 'POST', body })
      this.mergePeople(res.people)
      await Promise.all([this.openThread(id), this.loadList(), this.refreshCounters()])
    },
    async saveDraft(p: ComposePayload, draftId: number | null): Promise<MailMessage> {
      const res = draftId
        ? await apiFetch<{ message: MailMessage, people: Record<string, MailPerson> }>(`/mail/drafts/${draftId}`, { method: 'PUT', body: p })
        : await apiFetch<{ message: MailMessage, people: Record<string, MailPerson> }>('/mail/drafts', { method: 'POST', body: p })
      this.mergePeople(res.people)
      await Promise.all([this.refreshCounters(), this.view.kind === 'folder' && this.view.folder === 'drafts' ? this.loadList() : Promise.resolve()])
      return res.message
    },
    async discardDraft(id: number) {
      await apiFetch(`/mail/drafts/${id}`, { method: 'DELETE' })
      await this.afterRemoval(id)
    },
  },
})
