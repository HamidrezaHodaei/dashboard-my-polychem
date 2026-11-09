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
              <Icon
                name="lucide:settings"
                class="size-4"
                aria-hidden="true"
              />
              تنظیمات
            </NuxtLink>
          </Button>
        </div>
      </div>

      <div class="mb-3 flex gap-2">
        <Button
          size="sm"
          :variant="unreadOnly ? 'outline' : 'default'"
          @click="setFilter(false)"
        >
          همه
        </Button>
        <Button
          size="sm"
          :variant="unreadOnly ? 'default' : 'outline'"
          @click="setFilter(true)"
        >
          خوانده‌نشده
          <span v-if="store.unread > 0">({{ toPersianDigits(store.unread) }})</span>
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
                  :class="n.type === 'TASK_OVERDUE' ? 'text-destructive' : n.type === 'TASK_DUE_SOON' ? 'text-amber-500' : 'text-primary'"
                  aria-hidden="true"
                />
                <span class="min-w-0 flex-1 text-right">
                  <span
                    class="block text-sm font-medium text-foreground"
                    dir="rtl"
                  >{{ n.title }}</span>
                  <span
                    v-if="n.body"
                    class="block text-sm leading-6"
                    dir="rtl"
                  >{{ n.body }}</span>
                  <span class="mt-1 flex items-center gap-x-1 text-xs text-muted-foreground">
                    <Icon
                      name="lucide:clock"
                      class="size-3.5"
                      aria-hidden="true"
                    />
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
            {{ unreadOnly ? 'اعلان خوانده‌نشده‌ای وجود ندارد.' : 'اعلانی وجود ندارد.' }}
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
const unreadOnly = ref(false)
const loading = ref(false)
const loadError = ref(false)

const iconFor = (type: string) => ({
  TASK_ASSIGNED: 'lucide:clipboard-list',
  TASK_REFERRED: 'lucide:corner-up-left',
  TASK_MENTION: 'lucide:at-sign',
  TASK_DUE_SOON: 'lucide:alarm-clock',
  TASK_OVERDUE: 'lucide:alarm-clock-off',
  REVIEW_RESULT: 'lucide:badge-check',
  REVIEW_RESUBMITTED: 'lucide:rotate-ccw',
  CHANGE_REQUEST: 'lucide:file-pen-line',
} as Record<string, string>)[type] ?? 'lucide:bell'

async function load(reset: boolean) {
  if (loading.value) return
  loading.value = true
  loadError.value = false
  try {
    const data = await store.fetchPage({
      beforeId: reset ? null : nextBeforeId.value,
      unreadOnly: unreadOnly.value,
      limit: PAGE_SIZE,
    })
    items.value = reset ? data.items : [...items.value, ...data.items]
    hasMore.value = data.has_more
    nextBeforeId.value = data.next_before_id
  }
  catch {
    loadError.value = true
  }
  finally {
    loading.value = false
  }
}

function setFilter(value: boolean) {
  if (unreadOnly.value === value) return
  unreadOnly.value = value
  load(true)
}

async function open(n: AppNotification) {
  if (!n.is_read) {
    store.markRead([n.id]).catch(() => {})
    items.value = items.value.map(x => (x.id === n.id ? { ...x, is_read: true } : x))
  }
  if (n.link) await navigateTo(n.link)
}

async function markAll() {
  await store.markAllRead()
  items.value = items.value.map(n => ({ ...n, is_read: true }))
  if (unreadOnly.value) items.value = []
}

onMounted(() => load(true))
</script>
