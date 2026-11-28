<!-- pages/access-management/users/activity/[id].vue
  «جزئیات فعالیت کاربر»: sessions (login / logout / IP / device) and a searchable activity timeline.
  Everything comes from rows the backend really recorded (audit_logs + user_sessions). Whatever was not
  recorded is shown as «ثبت نشده» -- nothing on this page is estimated or invented. -->
<template>
  <ContainerWrapper class="space-y-5 py-6 md:py-8" dir="rtl">
    <nav class="flex flex-wrap items-center gap-2 text-sm text-muted-foreground" aria-label="مسیر">
      <NuxtLink to="/access-management/users" class="hover:text-foreground">کاربران</NuxtLink>
      <span aria-hidden="true">/</span>
      <NuxtLink :to="`/access-management/users/${userId}`" class="hover:text-foreground">{{ user?.full_name || '…' }}</NuxtLink>
      <span aria-hidden="true">/</span>
      <span>جزئیات فعالیت</span>
    </nav>

    <p v-if="loadError" class="rounded-md border border-destructive/40 p-4 text-sm text-destructive">
      {{ loadError }}
    </p>

    <template v-else>
      <header class="flex flex-col gap-3 border-b pb-5 md:flex-row md:items-end md:justify-between">
        <div>
          <h1 class="text-xl font-semibold md:text-2xl">
            جزئیات فعالیت · {{ user?.full_name || '…' }}
          </h1>
          <p class="mt-1 text-sm text-muted-foreground">
            {{ user?.username }}<span v-if="user?.email"> · {{ user.email }}</span>
          </p>
        </div>
        <dl class="grid grid-cols-2 gap-x-6 gap-y-1 text-sm md:text-end">
          <dt class="text-muted-foreground">آخرین ورود</dt>
          <dd class="tabular-nums">{{ user?.last_login_at ? formatTehranDateTime(user.last_login_at) : 'هرگز' }}</dd>
          <dt class="text-muted-foreground">نشست فعال</dt>
          <dd class="tabular-nums">{{ toPersianDigits(activeSessions) }}</dd>
        </dl>
      </header>

      <div class="rounded-md border bg-muted/30 p-3 text-sm leading-7 text-muted-foreground">
        <p>
          در این صفحه فقط آنچه سامانه واقعاً ثبت کرده نمایش داده می‌شود: ورود و خروج، و عملیات ایجاد، ویرایش و حذف.
          بازدید از صفحات و جست‌وجوها ثبت نمی‌شود.
        </p>
        <p v-if="recordingSince">
          اطلاعات IP، دستگاه، سیستم‌عامل و مرورگر برای ورودهای پس از {{ formatTehranDate(recordingSince) }} ثبت شده است؛
          برای ورودهای قدیم‌تر، این موارد «{{ NOT_RECORDED }}» نمایش داده می‌شوند.
        </p>
        <p v-else>
          هنوز هیچ نشستی با جزئیات دستگاه ثبت نشده است؛ از ورود بعدی کاربران ثبت می‌شود.
        </p>
      </div>

      <div role="tablist" class="flex gap-1 border-b">
        <button
          v-for="t in tabs"
          :key="t.id"
          role="tab"
          :aria-selected="tab === t.id"
          class="-mb-px h-11 border-b-2 px-4 text-sm"
          :class="tab === t.id ? 'border-primary font-medium text-foreground' : 'border-transparent text-muted-foreground hover:text-foreground'"
          @click="tab = t.id"
        >
          {{ t.label }}
        </button>
      </div>

      <!-- ===================== timeline ===================== -->
      <section v-show="tab === 'timeline'" class="space-y-4">
        <div class="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          <div class="relative">
            <Icon name="lucide:search" class="pointer-events-none absolute left-3 top-2.5 size-4 text-muted-foreground" />
            <Input v-model="tl.q" class="pl-9" placeholder="جستجو در فعالیت‌ها یا IP" />
          </div>
          <Select v-model="tl.category">
            <SelectTrigger class="w-full"><SelectValue placeholder="نوع" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="all">همهٔ رویدادها</SelectItem>
              <SelectItem value="auth">فقط ورود و خروج</SelectItem>
              <SelectItem value="action">فقط عملیات در پنل</SelectItem>
            </SelectContent>
          </Select>
          <Select v-model="tl.sort">
            <SelectTrigger class="w-full"><SelectValue placeholder="مرتب‌سازی" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="newest">جدیدترین</SelectItem>
              <SelectItem value="oldest">قدیمی‌ترین</SelectItem>
            </SelectContent>
          </Select>
          <Button variant="outline" class="h-9" :disabled="tl.loading" @click="loadTimeline()">بازآوری</Button>
        </div>
        <div class="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <div class="space-y-1">
            <Label class="text-xs text-muted-foreground">از تاریخ</Label>
            <JalaliDateInput v-model="tl.from" :max="tl.to || undefined" />
          </div>
          <div class="space-y-1">
            <Label class="text-xs text-muted-foreground">تا تاریخ</Label>
            <JalaliDateInput v-model="tl.to" :min="tl.from || undefined" />
          </div>
          <div v-if="tl.from || tl.to" class="flex items-end">
            <Button variant="ghost" size="sm" @click="tl.from = ''; tl.to = ''">حذف فیلتر تاریخ</Button>
          </div>
        </div>

        <p v-if="tl.error" class="p-6 text-center text-sm text-destructive">{{ tl.error }}</p>
        <p v-else-if="tl.loading && !tl.items.length" class="p-6 text-center text-sm text-muted-foreground">در حال بارگذاری…</p>
        <p v-else-if="!tl.items.length" class="rounded-md border p-8 text-center text-sm text-muted-foreground">
          فعالیتی با این فیلتر ثبت نشده است.
        </p>

        <div v-else class="space-y-5">
          <section v-for="g in timelineGroups" :key="g.day" aria-label="روز">
            <h3 class="sticky top-0 z-10 mb-2 border-b bg-background/95 py-1.5 text-sm font-semibold backdrop-blur">
              {{ formatDayHeading(g.day) }}
            </h3>
            <ol class="divide-y rounded-md border">
              <li v-for="ev in g.items" :key="ev.id" class="grid gap-x-4 gap-y-1 p-3 text-sm md:grid-cols-[5.5rem_minmax(0,1.4fr)_minmax(0,1fr)_minmax(0,1.2fr)] md:items-start">
                <time class="tabular-nums text-muted-foreground" :datetime="ev.at || undefined">{{ formatTehranTime(ev.at, true) }}</time>
                <div class="min-w-0">
                  <p class="font-medium">
                    {{ actionLabel(ev.action) }}
                    <span v-if="ev.entity_type" class="font-normal text-muted-foreground">
                      · {{ entityLabel(ev.entity_type) }}<template v-if="ev.entity_id"> {{ toPersianDigits(`#${ev.entity_id}`) }}</template>
                    </span>
                  </p>
                  <p v-if="ev.changed_fields.length" class="mt-0.5 text-xs text-muted-foreground">
                    فیلدهای تغییریافته: {{ ev.changed_fields.join('، ') }}
                  </p>
                  <p v-if="ev.reason" class="mt-0.5 text-xs text-muted-foreground">{{ logoutReasonLabel(ev.reason) }}</p>
                </div>
                <p class="text-muted-foreground">
                  <span class="md:hidden">بخش: </span>{{ moduleLabel(ev.module) }}
                </p>
                <p class="min-w-0 text-xs text-muted-foreground">
                  <span dir="ltr" class="tabular-nums">
                    <template v-if="ev.ip_address">{{ ev.ip_address }}</template>
                  </span>
                  <span v-if="!ev.ip_address">IP {{ NOT_RECORDED }}</span>
                  <template v-if="ev.category === 'auth'">
                    <br>
                    <span v-if="describeClient(ev)">{{ describeClient(ev) }}</span>
                    <span v-else>دستگاه {{ NOT_RECORDED }}</span>
                  </template>
                </p>
              </li>
            </ol>
          </section>

          <div class="flex flex-col gap-2 text-sm text-muted-foreground sm:flex-row sm:items-center sm:justify-between">
            <span>{{ toPersianDigits(tl.total) }} رویداد · صفحهٔ {{ toPersianDigits(tl.page) }} از {{ toPersianDigits(tlPages) }}</span>
            <div class="flex gap-2">
              <Button variant="outline" class="h-10 flex-1 sm:flex-none" :disabled="tl.page <= 1 || tl.loading" @click="tl.page--; loadTimeline(false)">قبلی</Button>
              <Button variant="outline" class="h-10 flex-1 sm:flex-none" :disabled="tl.page >= tlPages || tl.loading" @click="tl.page++; loadTimeline(false)">بعدی</Button>
            </div>
          </div>
        </div>
      </section>

      <!-- ===================== sessions ===================== -->
      <section v-show="tab === 'sessions'" class="space-y-4">
        <div class="flex flex-wrap items-center gap-3">
          <Select v-model="ss.status">
            <SelectTrigger class="w-full sm:w-48"><SelectValue placeholder="وضعیت نشست" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="all">همهٔ نشست‌ها</SelectItem>
              <SelectItem value="active">فعال</SelectItem>
              <SelectItem value="ended">خاتمه‌یافته</SelectItem>
              <SelectItem value="expired">منقضی‌شده</SelectItem>
            </SelectContent>
          </Select>
          <Button variant="outline" class="h-9" :disabled="ss.loading" @click="loadSessions()">بازآوری</Button>
        </div>

        <p v-if="ss.error" class="p-6 text-center text-sm text-destructive">{{ ss.error }}</p>
        <p v-else-if="ss.loading && !ss.items.length" class="p-6 text-center text-sm text-muted-foreground">در حال بارگذاری…</p>
        <p v-else-if="!ss.items.length" class="rounded-md border p-8 text-center text-sm text-muted-foreground">
          نشستی ثبت نشده است. نشست‌ها از زمان فعال‌شدن این قابلیت ثبت می‌شوند.
        </p>

        <template v-else>
          <div class="hidden rounded-md border md:block">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>وضعیت</TableHead>
                  <TableHead>ورود</TableHead>
                  <TableHead>آخرین فعالیت</TableHead>
                  <TableHead>خروج</TableHead>
                  <TableHead>IP</TableHead>
                  <TableHead>دستگاه</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                <TableRow v-for="s in ss.items" :key="s.id">
                  <TableCell><Badge :variant="s.status === 'active' ? 'default' : 'outline'">{{ sessionStatusLabel(s.status) }}</Badge></TableCell>
                  <TableCell class="whitespace-nowrap tabular-nums">{{ formatTehranDateTimeSeconds(s.login_at) }}</TableCell>
                  <TableCell class="whitespace-nowrap tabular-nums">{{ s.last_seen_at ? formatTehranDateTimeSeconds(s.last_seen_at) : NOT_RECORDED }}</TableCell>
                  <TableCell>
                    <template v-if="s.logout_at">
                      <span class="whitespace-nowrap tabular-nums">{{ formatTehranDateTimeSeconds(s.logout_at) }}</span>
                      <p class="text-xs text-muted-foreground">{{ logoutReasonLabel(s.logout_reason) }}</p>
                    </template>
                    <span v-else class="text-muted-foreground">{{ s.status === 'active' ? 'هنوز خارج نشده' : 'خروج ثبت نشده (نشست منقضی شد)' }}</span>
                  </TableCell>
                  <TableCell dir="ltr" class="text-right tabular-nums">
                    <template v-if="s.ip_address">{{ s.ip_address }}</template>
                    <span v-else class="text-xs text-muted-foreground" dir="rtl">{{ NOT_RECORDED }}</span>
                  </TableCell>
                  <TableCell>
                    <template v-if="describeClient(s)">{{ describeClient(s) }}</template>
                    <span v-else class="text-xs text-muted-foreground">{{ NOT_RECORDED }}</span>
                  </TableCell>
                </TableRow>
              </TableBody>
            </Table>
          </div>

          <ul class="space-y-3 md:hidden">
            <li v-for="s in ss.items" :key="s.id" class="space-y-2 rounded-md border p-4">
              <div class="flex items-center justify-between">
                <Badge :variant="s.status === 'active' ? 'default' : 'outline'">{{ sessionStatusLabel(s.status) }}</Badge>
                <span class="text-xs text-muted-foreground">{{ describeClient(s) || `دستگاه ${NOT_RECORDED}` }}</span>
              </div>
              <dl class="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-sm">
                <dt class="text-muted-foreground">ورود</dt>
                <dd class="tabular-nums">{{ formatTehranDateTimeSeconds(s.login_at) }}</dd>
                <dt class="text-muted-foreground">خروج</dt>
                <dd class="tabular-nums">{{ s.logout_at ? formatTehranDateTimeSeconds(s.logout_at) : (s.status === 'active' ? 'هنوز خارج نشده' : 'ثبت نشده') }}</dd>
                <dt class="text-muted-foreground">IP</dt>
                <dd dir="ltr" class="text-right tabular-nums">{{ s.ip_address || NOT_RECORDED }}</dd>
              </dl>
            </li>
          </ul>

          <div class="flex flex-col gap-2 text-sm text-muted-foreground sm:flex-row sm:items-center sm:justify-between">
            <span>{{ toPersianDigits(ss.total) }} نشست · صفحهٔ {{ toPersianDigits(ss.page) }} از {{ toPersianDigits(ssPages) }}</span>
            <div class="flex gap-2">
              <Button variant="outline" class="h-10 flex-1 sm:flex-none" :disabled="ss.page <= 1 || ss.loading" @click="ss.page--; loadSessions(false)">قبلی</Button>
              <Button variant="outline" class="h-10 flex-1 sm:flex-none" :disabled="ss.page >= ssPages || ss.loading" @click="ss.page++; loadSessions(false)">بعدی</Button>
            </div>
          </div>
        </template>
      </section>
    </template>
  </ContainerWrapper>
</template>

<script setup lang="ts">
import { ApiError, apiFetch, apiFetchPage } from '~/services/backendApi'
import type { ActivityEvent, UserSessionRow } from '~/utils/activity'

definePageMeta({ title: 'جزئیات فعالیت کاربر' })

interface BackendUser { id: number, full_name: string, username: string, email: string, last_login_at: string | null }

const route = useRoute()
const userId = Number(route.params.id)
const PER_PAGE = 25

const user = ref<BackendUser | null>(null)
const loadError = ref('')
const tab = ref<'timeline' | 'sessions'>('timeline')
const tabs = [{ id: 'timeline', label: 'خط زمانی فعالیت' }, { id: 'sessions', label: 'نشست‌ها' }] as const

const tl = reactive({
  q: '', category: 'all', sort: 'newest', from: '', to: '',
  page: 1, total: 0, items: [] as ActivityEvent[], loading: false, error: '',
})
const ss = reactive({
  status: 'all', page: 1, total: 0, items: [] as UserSessionRow[], loading: false, error: '',
})
const recordingSince = ref<string | null>(null)
const activeSessions = ref(0)

const tlPages = computed(() => Math.max(1, Math.ceil(tl.total / PER_PAGE)))
const ssPages = computed(() => Math.max(1, Math.ceil(ss.total / PER_PAGE)))

const timelineGroups = computed(() => {
  const groups: { day: string, items: ActivityEvent[] }[] = []
  for (const ev of tl.items) {
    const day = tehranDayKey(ev.at)
    const last = groups[groups.length - 1]
    if (last && last.day === day) last.items.push(ev)
    else groups.push({ day, items: [ev] })
  }
  return groups
})

async function loadTimeline(reset = true) {
  if (reset) tl.page = 1
  tl.loading = true
  tl.error = ''
  try {
    const res = await apiFetchPage<ActivityEvent>(`/core/users/${userId}/activity/timeline`, {
      q: tl.q.trim() || undefined,
      category: tl.category === 'all' ? undefined : tl.category,
      date_from: tl.from || undefined,
      date_to: tl.to || undefined,
      sort: tl.sort,
      page: tl.page,
      per_page: PER_PAGE,
    })
    tl.items = res.items
    tl.total = res.total
  }
  catch (e) { tl.error = e instanceof ApiError ? e.message : 'بارگذاری فعالیت‌ها ناموفق بود.' }
  finally { tl.loading = false }
}

async function loadSessions(reset = true) {
  if (reset) ss.page = 1
  ss.loading = true
  ss.error = ''
  try {
    const res = await apiFetchPage<UserSessionRow>(`/core/users/${userId}/activity/sessions`, {
      status: ss.status === 'all' ? undefined : ss.status,
      page: ss.page,
      per_page: PER_PAGE,
    })
    ss.items = res.items
    ss.total = res.total
    recordingSince.value = (res.meta?.recording_since as string | null | undefined) ?? null
  }
  catch (e) { ss.error = e instanceof ApiError ? e.message : 'بارگذاری نشست‌ها ناموفق بود.' }
  finally { ss.loading = false }
}

async function loadActiveCount() {
  try {
    const res = await apiFetchPage<UserSessionRow>(`/core/users/${userId}/activity/sessions`, { status: 'active', per_page: 1 })
    activeSessions.value = res.total
  }
  catch { /* the header number is secondary */ }
}

let timer: ReturnType<typeof setTimeout> | undefined
watch(() => tl.q, () => { clearTimeout(timer); timer = setTimeout(() => loadTimeline(), 300) })
watch(() => [tl.category, tl.sort, tl.from, tl.to], () => loadTimeline())
watch(() => ss.status, () => loadSessions())
onBeforeUnmount(() => clearTimeout(timer))

onMounted(async () => {
  if (!Number.isInteger(userId)) { loadError.value = 'شناسهٔ کاربر نامعتبر است.'; return }
  try {
    user.value = await apiFetch<BackendUser>(`/core/users/${userId}`)
  }
  catch (e) {
    loadError.value = e instanceof ApiError ? e.message : 'بارگذاری کاربر ناموفق بود.'
    return
  }
  await Promise.all([loadTimeline(), loadSessions(), loadActiveCount()])
})
</script>
