<!-- components/access/AccessLoginEvents.vue
  Login / logout / failed-login events of every user the viewer may read, in Jalali (Tehran) time.
  Source: GET /api/core/users/login-events (audit_logs, module "auth"). Fields the server never
  recorded (e.g. the IP on very old rows) are shown as «ثبت نشده», never filled in. -->
<template>
  <Card class="overflow-hidden py-0 shadow-none">
    <div class="space-y-3 border-b p-4">
      <div class="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        <div class="relative">
          <Icon name="lucide:search" class="pointer-events-none absolute left-3 top-2.5 size-4 text-muted-foreground" />
          <Input v-model="q" class="pl-9" placeholder="جستجو: نام، نام کاربری یا IP" />
        </div>
        <Select v-model="event">
          <SelectTrigger class="w-full">
            <SelectValue placeholder="نوع رویداد" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">همهٔ رویدادها</SelectItem>
            <SelectItem value="login_success">ورود موفق</SelectItem>
            <SelectItem value="logout">خروج</SelectItem>
            <SelectItem value="login_failure">ورود ناموفق</SelectItem>
          </SelectContent>
        </Select>
        <Select v-model="sort">
          <SelectTrigger class="w-full">
            <SelectValue placeholder="مرتب‌سازی" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="newest">جدیدترین</SelectItem>
            <SelectItem value="oldest">قدیمی‌ترین</SelectItem>
          </SelectContent>
        </Select>
        <Button variant="outline" :disabled="loading" @click="load()">
          بازآوری
        </Button>
      </div>
      <div class="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <div class="space-y-1">
          <Label class="text-xs text-muted-foreground">از تاریخ</Label>
          <JalaliDateInput v-model="dateFrom" :max="dateTo || undefined" />
        </div>
        <div class="space-y-1">
          <Label class="text-xs text-muted-foreground">تا تاریخ</Label>
          <JalaliDateInput v-model="dateTo" :min="dateFrom || undefined" />
        </div>
        <div v-if="dateFrom || dateTo" class="flex items-end">
          <Button variant="ghost" size="sm" @click="dateFrom = ''; dateTo = ''">
            حذف فیلتر تاریخ
          </Button>
        </div>
      </div>
    </div>

    <p v-if="error" class="p-6 text-center text-sm text-destructive">
      {{ error }}
    </p>
    <p v-else-if="loading && !rows.length" class="p-6 text-center text-sm text-muted-foreground">
      در حال بارگذاری…
    </p>
    <p v-else-if="!rows.length" class="p-8 text-center text-sm text-muted-foreground">
      رویدادی با این فیلتر ثبت نشده است.
    </p>

    <template v-else>
      <!-- desktop / tablet: table -->
      <div class="hidden md:block">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>تاریخ و ساعت</TableHead>
              <TableHead>کاربر</TableHead>
              <TableHead>رویداد</TableHead>
              <TableHead>IP</TableHead>
              <TableHead>دستگاه</TableHead>
              <TableHead class="w-28 text-center">جزئیات</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            <TableRow v-for="row in rows" :key="row.id">
              <TableCell class="whitespace-nowrap tabular-nums" dir="ltr">
                <span class="block text-right">{{ formatTehranDateTimeSeconds(row.at) }}</span>
              </TableCell>
              <TableCell>
                <NuxtLink v-if="row.user" :to="`/access-management/users/${row.user.id}`" class="font-medium hover:underline">
                  {{ row.user.full_name }}
                </NuxtLink>
                <p v-if="row.user" class="text-xs text-muted-foreground">
                  {{ row.user.username }}
                </p>
              </TableCell>
              <TableCell>
                <Badge :variant="row.action === 'login_failure' ? 'destructive' : 'outline'">
                  {{ actionLabel(row.action) }}
                </Badge>
              </TableCell>
              <TableCell dir="ltr" class="text-right">
                <span v-if="row.ip_address" class="tabular-nums">{{ row.ip_address }}</span>
                <span v-else class="text-xs text-muted-foreground">{{ NOT_RECORDED }}</span>
              </TableCell>
              <TableCell>
                <span v-if="describeClient(row)">{{ describeClient(row) }}</span>
                <span v-else class="text-xs text-muted-foreground">{{ NOT_RECORDED }}</span>
              </TableCell>
              <TableCell class="text-center">
                <Button v-if="row.user" variant="outline" size="sm" as-child>
                  <NuxtLink :to="`/access-management/users/activity/${row.user.id}`">
                    جزئیات فعالیت
                  </NuxtLink>
                </Button>
              </TableCell>
            </TableRow>
          </TableBody>
        </Table>
      </div>

      <!-- phone: one stacked record per event, no horizontal scroll -->
      <ul class="divide-y md:hidden">
        <li v-for="row in rows" :key="row.id" class="space-y-2 p-4">
          <div class="flex items-start justify-between gap-3">
            <div class="min-w-0">
              <p class="truncate font-medium">{{ row.user?.full_name }}</p>
              <p class="text-xs text-muted-foreground">{{ row.user?.username }}</p>
            </div>
            <Badge :variant="row.action === 'login_failure' ? 'destructive' : 'outline'" class="shrink-0">
              {{ actionLabel(row.action) }}
            </Badge>
          </div>
          <dl class="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-sm">
            <dt class="text-muted-foreground">زمان</dt>
            <dd class="tabular-nums">{{ formatTehranDateTimeSeconds(row.at) }}</dd>
            <dt class="text-muted-foreground">IP</dt>
            <dd dir="ltr" class="text-right tabular-nums">
              <span v-if="row.ip_address">{{ row.ip_address }}</span>
              <span v-else class="text-muted-foreground" dir="rtl">{{ NOT_RECORDED }}</span>
            </dd>
            <dt class="text-muted-foreground">دستگاه</dt>
            <dd>
              <span v-if="describeClient(row)">{{ describeClient(row) }}</span>
              <span v-else class="text-muted-foreground">{{ NOT_RECORDED }}</span>
            </dd>
          </dl>
          <Button v-if="row.user" variant="outline" class="h-11 w-full" as-child>
            <NuxtLink :to="`/access-management/users/activity/${row.user.id}`">
              جزئیات فعالیت
            </NuxtLink>
          </Button>
        </li>
      </ul>

      <div class="flex flex-col gap-2 border-t p-4 text-sm text-muted-foreground sm:flex-row sm:items-center sm:justify-between">
        <span>{{ toPersianDigits(total) }} رویداد · صفحهٔ {{ toPersianDigits(page) }} از {{ toPersianDigits(totalPages) }}</span>
        <div class="flex gap-2">
          <Button variant="outline" class="h-10 flex-1 sm:flex-none" :disabled="page <= 1 || loading" @click="page--; load(false)">
            قبلی
          </Button>
          <Button variant="outline" class="h-10 flex-1 sm:flex-none" :disabled="page >= totalPages || loading" @click="page++; load(false)">
            بعدی
          </Button>
        </div>
      </div>
    </template>
  </Card>
</template>

<script setup lang="ts">
import { ApiError, apiFetchPage } from '~/services/backendApi'
import type { ActivityEvent } from '~/utils/activity'

const PER_PAGE = 20
const q = ref('')
const event = ref('all')
const sort = ref('newest')
const dateFrom = ref('')
const dateTo = ref('')
const page = ref(1)
const total = ref(0)
const rows = ref<ActivityEvent[]>([])
const loading = ref(false)
const error = ref('')
const totalPages = computed(() => Math.max(1, Math.ceil(total.value / PER_PAGE)))

async function load(reset = true) {
  if (reset) page.value = 1
  loading.value = true
  error.value = ''
  try {
    const res = await apiFetchPage<ActivityEvent>('/core/users/login-events', {
      q: q.value.trim() || undefined,
      event: event.value === 'all' ? undefined : event.value,
      date_from: dateFrom.value || undefined,
      date_to: dateTo.value || undefined,
      sort: sort.value,
      page: page.value,
      per_page: PER_PAGE,
    })
    rows.value = res.items
    total.value = res.total
  }
  catch (e) {
    error.value = e instanceof ApiError ? e.message : 'بارگذاری رویدادها ناموفق بود.'
  }
  finally { loading.value = false }
}

let timer: ReturnType<typeof setTimeout> | undefined
watch(q, () => { clearTimeout(timer); timer = setTimeout(() => load(), 300) })
watch([event, sort, dateFrom, dateTo], () => load())
onMounted(() => load())
onBeforeUnmount(() => clearTimeout(timer))
</script>
