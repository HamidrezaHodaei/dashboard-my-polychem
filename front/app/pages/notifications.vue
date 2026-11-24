<template>
  <ContainerWrapper>
    <div
      dir="rtl"
      class="mx-auto max-w-3xl text-right"
    >
      <div class="mb-6 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <h1 class="text-2xl font-bold tracking-tight md:text-3xl">
          همه اعلانات
        </h1>
        <div class="flex items-center gap-2">
          <Button
            v-if="store.unread > 0"
            variant="outline"
            size="sm"
            @click="markAll"
          >
            همه را خوانده‌شده کن
          </Button>
          <Button
            variant="ghost"
            size="sm"
            as-child
          >
            <NuxtLink to="/settings/notifications">
              تنظیمات
            </NuxtLink>
          </Button>
        </div>
      </div>

      <!-- Push is the way notifications reach a closed app: offer it here, where the user is looking at them. -->
      <div
        v-if="push.canOffer.value"
        class="mb-4 flex flex-col gap-2 rounded-lg border bg-muted/30 p-3 sm:flex-row sm:items-center sm:justify-between"
      >
        <p class="text-sm text-muted-foreground">
          {{ push.needsInstall.value ? 'برای دریافت اعلان روی آیفون، ابتدا سامانه را به صفحه اصلی اضافه کنید.' : 'اعلان‌های فوری فعال نیست؛ با فعال‌سازی، حتی وقتی برنامه بسته است اعلان می‌گیرید.' }}
        </p>
        <Button
          size="sm"
          variant="outline"
          as-child
        >
          <NuxtLink to="/settings/notifications">
            فعال‌سازی
          </NuxtLink>
        </Button>
      </div>

      <div class="mb-3 grid gap-2 sm:grid-cols-[1fr_auto]">
        <Input
          v-model="query"
          type="search"
          dir="rtl"
          placeholder="جستجو در عنوان و متن اعلان‌ها"
          aria-label="جستجو در اعلان‌ها"
          autocomplete="off"
        />
        <NativeSelect
          v-model="category"
          dir="rtl"
          class="w-full sm:w-48"
          aria-label="دسته اعلان"
        >
          <NativeSelectOption value="">
            همه دسته‌ها
          </NativeSelectOption>
          <NativeSelectOption
            v-for="c in NOTIFICATION_CATEGORIES"
            :key="c.key"
            :value="c.key"
          >
            {{ c.label }}
          </NativeSelectOption>
        </NativeSelect>
      </div>

      <div
        class="mb-3 flex flex-wrap gap-2"
        role="group"
        aria-label="وضعیت خواندن"
      >
        <Button
          v-for="f in readFilters"
          :key="f.value"
          size="sm"
          :variant="readFilter === f.value ? 'default' : 'outline'"
          :aria-pressed="readFilter === f.value"
          @click="setFilter(f.value)"
        >
          {{ f.label }}
          <span v-if="f.value === 'unread' && store.unread > 0">({{ toPersianDigits(store.unread) }})</span>
        </Button>
      </div>

      <Card class="overflow-hidden shadow-none">
        <ul class="divide-y">
          <li
            v-for="n in items"
            :key="n.id"
          >
            <button
              type="button"
              dir="rtl"
              class="block w-full px-4 py-3 text-right transition-colors hover:bg-accent hover:text-accent-foreground"
              :class="n.is_read ? 'text-foreground/70' : 'bg-primary/5'"
              @click="open(n)"
            >
              <span class="flex items-start gap-3">
                <Icon
                  :name="iconFor(n.type)"
                  class="mt-0.5 size-5 shrink-0"
                  :class="iconColor(n.type)"
                  aria-hidden="true"
                />
                <span class="min-w-0 flex-1 text-right">
                  <span
                    class="block whitespace-pre-line text-sm font-medium text-foreground [overflow-wrap:anywhere]"
                    dir="rtl"
                  >{{ n.title }}</span>
                  <span
                    v-if="n.body"
                    class="block whitespace-pre-line text-sm leading-6 [overflow-wrap:anywhere]"
                    dir="rtl"
                  >{{ n.body }}</span>
                  <span class="mt-1 flex items-center gap-x-1 text-xs text-muted-foreground">
                    <span dir="rtl">{{ formatNotificationDateTime(n.created_at) }}</span>
                  </span>
                </span>
                <span
                  v-if="!n.is_read"
                  class="mt-2 size-2 shrink-0 rounded-full bg-primary"
                  aria-label="خوانده‌نشده"
                />
              </span>
            </button>
          </li>
          <li
            v-if="!items.length && !loading"
            class="px-4 py-12 text-center text-sm text-muted-foreground"
          >
            {{ emptyText }}
          </li>
          <li
            v-if="loading && !items.length"
            class="px-4 py-12 text-center text-sm text-muted-foreground"
          >
            در حال بارگذاری…
          </li>
        </ul>
      </Card>

      <div
        v-if="hasMore"
        class="mt-4 flex justify-center"
      >
        <Button
          variant="outline"
          :disabled="loading"
          @click="load(false)"
        >
          {{ loading ? 'در حال بارگذاری…' : 'نمایش بیشتر' }}
        </Button>
      </div>
      <p
        v-if="loadError"
        class="mt-3 text-center text-sm text-destructive"
      >
        بارگذاری اعلانات انجام نشد. دوباره تلاش کنید.
      </p>
    </div>
  </ContainerWrapper>
</template>

<script lang="ts" setup>
import type { AppNotification } from '~/stores/notifications'

definePageMeta({ title: 'همه اعلانات' })
usePageSeoMeta({ title: 'همه اعلانات' })

const PAGE_SIZE = 30
const store = useNotificationsStore()

const items = ref<AppNotification[]>([])
const hasMore = ref(false)
const nextBeforeId = ref<number | null>(null)
const readFilter = ref<'all' | 'unread' | 'read'>('all')
const query = ref('')
const category = ref('')
const loading = ref(false)
const loadError = ref(false)
const push = usePush()
let requestSeq = 0

const readFilters = [
  { value: 'all', label: 'همه' },
  { value: 'unread', label: 'خوانده‌نشده' },
  { value: 'read', label: 'خوانده‌شده' },
] as const

const iconFor = notificationIcon
const iconColor = notificationIconColor
const filtered = computed(() => !!query.value.trim() || !!category.value || readFilter.value !== 'all')
const emptyText = computed(() => (filtered.value ? 'اعلانی با این شرایط پیدا نشد.' : 'اعلانی وجود ندارد.'))

async function load(reset: boolean) {
  if (loading.value && !reset) return
  const seq = ++requestSeq // a newer search/filter makes an older, slower answer irrelevant
  loading.value = true
  loadError.value = false
  try {
    const data = await store.fetchPage({
      beforeId: reset ? null : nextBeforeId.value,
      read: readFilter.value,
      q: query.value,
      category: category.value,
      limit: PAGE_SIZE,
    })
    if (seq !== requestSeq) return
    items.value = reset ? data.items : [...items.value, ...data.items]
    hasMore.value = data.has_more
    nextBeforeId.value = data.next_before_id
  }
  catch {
    if (seq === requestSeq) loadError.value = true
  }
  finally {
    if (seq === requestSeq) loading.value = false
  }
}

function setFilter(value: 'all' | 'unread' | 'read') {
  if (readFilter.value === value) return
  readFilter.value = value
  load(true)
}

let searchTimer: ReturnType<typeof setTimeout> | null = null
watch(query, () => {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => load(true), 350)
})
watch(category, () => load(true))
onBeforeUnmount(() => { if (searchTimer) clearTimeout(searchTimer) })

async function open(n: AppNotification) {
  if (!n.is_read) {
    store.markRead([n.id]).catch(() => {})
    items.value = items.value.map(x => (x.id === n.id ? { ...x, is_read: true } : x))
  }
  // older notifications were saved with the bare `/crm` link -- send them to the customer bank
  if (n.link) await navigateTo(n.link === '/crm' ? '/crm/customers' : n.link)
}

async function markAll() {
  await store.markAllRead()
  items.value = items.value.map(n => ({ ...n, is_read: true }))
  if (readFilter.value === 'unread') items.value = []
}

onMounted(() => {
  load(true)
  push.refreshState()
})
</script>
