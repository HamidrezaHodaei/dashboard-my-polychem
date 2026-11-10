<template>
  <Popover v-model:open="open">
    <PopoverTrigger as-child>
      <Button
        variant="ghost"
        size="icon"
        aria-label="اعلان‌ها"
      >
        <div class="relative flex items-center">
          <Icon
            name="lucide:bell"
            class="text-xl size-5"
            aria-hidden="true"
          />
          <span class="sr-only">اعلان‌ها</span>
          <span
            v-if="store.unread > 0"
            class="absolute -top-2 -right-2 flex min-w-4 items-center justify-center rounded-full bg-destructive px-1 text-[10px] font-semibold leading-4 text-white"
          >
            {{ store.unread > 99 ? '۹۹+' : toPersianDigits(store.unread) }}
          </span>
        </div>
      </Button>
    </PopoverTrigger>

    <PopoverContent
      side="bottom"
      dir="rtl"
      class="w-72 p-0 text-right"
    >
      <div class="flex items-center justify-between px-3 pb-1.5 pt-2.5">
        <span class="text-sm font-semibold">اعلان‌ها</span>
        <Button
          v-if="store.unread > 0"
          variant="link"
          size="sm"
          class="h-auto p-0 text-xs"
          @click="store.markAllRead()"
        >
          همه را خوانده‌شده کن
        </Button>
      </div>

      <ul class="max-h-64 divide-y overflow-y-auto border-t">
        <li
          v-for="n in latest"
          :key="n.id"
        >
          <button
            type="button"
            dir="rtl"
            class="block w-full px-3 py-2 text-right transition-colors hover:bg-accent hover:text-accent-foreground"
            :class="n.is_read ? 'text-foreground/70' : 'bg-primary/5'"
            @click="openNotification(n)"
          >
            <span class="flex items-start gap-2">
              <Icon
                :name="iconFor(n.type)"
                class="mt-0.5 size-4 shrink-0"
                :class="n.type === 'TASK_OVERDUE' ? 'text-destructive' : n.type === 'TASK_DUE_SOON' ? 'text-amber-500' : 'text-primary'"
                aria-hidden="true"
              />
              <span class="min-w-0 flex-1 text-right">
                <span
                  class="block truncate text-[13px] font-medium text-foreground"
                  dir="rtl"
                >{{ n.title }}</span>
                <span
                  v-if="n.body"
                  class="block text-xs leading-5 line-clamp-2"
                  dir="rtl"
                >{{ n.body }}</span>
                <span class="mt-0.5 flex items-center gap-x-1 text-[11px] text-muted-foreground">
                  <Icon
                    name="lucide:clock"
                    class="size-3"
                    aria-hidden="true"
                  />
                  <span dir="rtl">{{ formatNotificationTime(n.created_at) }}</span>
                </span>
              </span>
              <span
                v-if="!n.is_read"
                class="mt-1.5 size-2 shrink-0 rounded-full bg-primary"
                aria-label="خوانده‌نشده"
              />
            </span>
          </button>
        </li>
        <li
          v-if="!latest.length"
          class="px-4 py-6 text-center text-sm text-muted-foreground"
        >
          اعلانی وجود ندارد.
        </li>
      </ul>

      <div class="flex items-center gap-1 border-t p-1.5">
        <Button
          variant="secondary"
          size="sm"
          class="h-8 flex-1 text-xs"
          @click="goAll"
        >
          مشاهده همه اعلانات
        </Button>
        <Button
          variant="ghost"
          size="icon"
          class="size-8 shrink-0"
          aria-label="تنظیمات اعلان‌ها"
          title="تنظیمات اعلان‌ها"
          @click="goSettings"
        >
          <Icon
            name="lucide:settings"
            class="size-4"
            aria-hidden="true"
          />
        </Button>
      </div>
    </PopoverContent>
  </Popover>
</template>

<script lang="ts" setup>
import type { AppNotification } from '~/stores/notifications'

/** the popover only previews the newest few; the full history lives on /notifications */
const PREVIEW_COUNT = 5

const store = useNotificationsStore()
const open = ref(false)
const latest = computed(() => store.items.slice(0, PREVIEW_COUNT))

onMounted(() => store.start())
onBeforeUnmount(() => store.stop())

const iconFor = (type: string) => ({
  TASK_ASSIGNED: 'lucide:clipboard-list',
  TASK_REFERRED: 'lucide:corner-up-left',
  TASK_MENTION: 'lucide:at-sign',
  TASK_DUE_SOON: 'lucide:alarm-clock',
  TASK_OVERDUE: 'lucide:alarm-clock-off',
  REVIEW_RESULT: 'lucide:badge-check',
  REVIEW_RESUBMITTED: 'lucide:rotate-ccw',
  CHANGE_REQUEST: 'lucide:file-pen-line',
  REVIEW_REQUEST: 'lucide:inbox',
} as Record<string, string>)[type] ?? 'lucide:bell'

async function openNotification(n: AppNotification) {
  open.value = false
  if (!n.is_read) store.markRead([n.id]).catch(() => {})
  // older notifications were saved with the bare `/crm` link -- send them to the customer bank
  if (n.link) await navigateTo(n.link === '/crm' ? '/crm/customers' : n.link)
}
async function goAll() {
  open.value = false
  await navigateTo('/notifications')
}
async function goSettings() {
  open.value = false
  await navigateTo('/settings/notifications')
}
</script>
