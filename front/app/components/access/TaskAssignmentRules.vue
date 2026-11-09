<template>
  <div class="space-y-6">
    <Card class="overflow-hidden py-0 shadow-none">
      <div class="border-b p-5">
        <h2 class="font-semibold">
          قوانین واگذاری وظایف
        </h2>
        <p class="mt-1 text-sm text-muted-foreground">
          تعیین کنید چه کسی بتواند برای چه افرادی وظیفه ایجاد کند یا وظایف را به آن‌ها واگذار کند. مدیران می‌توانند این کارها را برای همه انجام دهند و هر کاربر نیز همیشه می‌تواند برای خودش وظیفه ایجاد یا واگذار کند. دسترسی سایر کاربران به قوانین زیر محدود است: «ایجاد» فقط اجازهٔ شروع وظایفی را می‌دهد که از قبل به فرد هدف واگذار شده‌اند؛ «واگذاری» فقط اجازهٔ واگذاری دوبارهٔ وظایف موجود را می‌دهد و «هر دو» هر دو دسترسی را فعال می‌کند. فقط مدیران و دارندگان مجوز <span class="font-mono">core.permission.update</span> می‌توانند این قوانین را ویرایش کنند.
        </p>
      </div>

      <div
        v-if="canManage"
        class="grid gap-4 border-b bg-muted/20 p-5 lg:grid-cols-[1fr_1fr_9rem_auto]"
      >
        <div class="space-y-1.5">
          <Label>چه کسی وظایف را تعریف می‌کند</Label>
          <div class="grid grid-cols-[8rem_1fr] gap-2">
            <Select v-model="form.grantor_type">
              <SelectTrigger class="w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="USER">
                  کاربر
                </SelectItem>
                <SelectItem value="ROLE">
                  نقش
                </SelectItem>
              </SelectContent>
            </Select>
            <Select v-model="form.grantor_id">
              <SelectTrigger class="w-full">
                <SelectValue placeholder="انتخاب کنید…" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem
                  v-for="o in grantorOptions"
                  :key="o.id"
                  :value="String(o.id)"
                >
                  {{ o.label }}
                </SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>

        <div class="space-y-1.5">
          <Label>می‌تواند وظایف را به چه کسی واگذار کند</Label>
          <div class="grid grid-cols-[8rem_1fr] gap-2">
            <Select v-model="form.target_type">
              <SelectTrigger class="w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="ALL">
                  همه
                </SelectItem>
                <SelectItem value="USER">
                  کاربر
                </SelectItem>
                <SelectItem value="ROLE">
                  نقش
                </SelectItem>
                <SelectItem value="DEPARTMENT">
                  دپارتمان
                </SelectItem>
                <SelectItem value="TEAM">
                  تیم
                </SelectItem>
              </SelectContent>
            </Select>
            <Select
              v-model="form.target_id"
              :disabled="form.target_type === 'ALL'"
            >
              <SelectTrigger class="w-full">
                <SelectValue :placeholder="form.target_type === 'ALL' ? 'همهٔ کاربران' : 'انتخاب کنید…'" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem
                  v-for="o in targetOptions"
                  :key="o.id"
                  :value="String(o.id)"
                >
                  {{ o.label }}
                </SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>

        <div class="space-y-1.5">
          <Label>عمل</Label>
          <Select v-model="form.action">
            <SelectTrigger class="w-full">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="BOTH">
                ایجاد و واگذاری
              </SelectItem>
              <SelectItem value="CREATE">
                فقط ایجاد
              </SelectItem>
              <SelectItem value="ASSIGN">
                فقط واگذاری
              </SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div class="flex items-end">
          <Button
            class="w-full gap-2 lg:w-auto"
            :disabled="!canSubmit || saving"
            @click="addRule"
          >
            <Icon
              name="lucide:plus"
              class="size-4"
            /> افزودن قانون
          </Button>
        </div>
      </div>

      <div
        v-if="loading"
        class="p-8 text-center text-sm text-muted-foreground"
      >
        در حال بارگذاری قوانین…
      </div>
      <div
        v-else-if="loadError"
        class="p-8 text-center text-sm text-destructive"
      >
        {{ loadError }}
      </div>
      <Table v-else-if="rules.length">
        <TableHeader>
          <TableRow>
            <TableHead>چه کسی</TableHead>
            <TableHead>می‌تواند وظایف را به چه کسی واگذار کند</TableHead>
            <TableHead>عمل</TableHead>
            <TableHead v-if="canManage" class="text-right">
              عملیات
            </TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          <TableRow
            v-for="r in rules"
            :key="r.id"
          >
            <TableCell>
              <Badge variant="outline">
                {{ assignmentTypeLabel(r.grantor_type) }}
              </Badge>
              <span class="ml-2 font-medium">{{ r.grantor_label }}</span>
            </TableCell>
            <TableCell>
              <Badge variant="secondary">
                {{ targetTypeLabel(r.target_type) }}
              </Badge>
              <span
                v-if="r.target_type !== 'ALL'"
                class="ml-2 font-medium"
              >{{ r.target_label }}</span>
            </TableCell>
            <TableCell>
              <Badge :variant="r.action === 'BOTH' ? 'secondary' : 'outline'">
                {{ actionLabel(r.action) }}
              </Badge>
            </TableCell>
            <TableCell
              v-if="canManage"
              class="text-right"
            >
              <Button
                variant="ghost"
                size="icon"
                class="text-destructive"
                title="حذف قانون"
                @click="removeRule(r)"
              >
                <Icon
                  name="lucide:trash-2"
                  class="size-4"
                />
              </Button>
            </TableCell>
          </TableRow>
        </TableBody>
      </Table>
      <div
        v-else
        class="p-8 text-center text-sm text-muted-foreground"
      >
        هنوز قانونی ثبت نشده است؛ فقط مدیران می‌توانند وظایف را به دیگران واگذار کنند.
      </div>
    </Card>
  </div>
</template>

<script setup lang="ts">
const notify = useNotify()
import { ApiError, apiFetch, apiFetchPage } from '~/services/backendApi'

interface Rule {
  id: number
  grantor_type: 'USER' | 'ROLE'
  grantor_id: number
  grantor_label: string
  target_type: 'ALL' | 'USER' | 'ROLE' | 'DEPARTMENT' | 'TEAM'
  target_id: number | null
  target_label: string
  action: 'CREATE' | 'ASSIGN' | 'BOTH'
}
interface Opt { id: number, label: string }

const auth = useAuthStore()
const rules = ref<Rule[]>([])
const loading = ref(false)
const loadError = ref('')
const saving = ref(false)
const canManage = ref(false)

const catalog = reactive<{ USER: Opt[], ROLE: Opt[], DEPARTMENT: Opt[], TEAM: Opt[] }>({
  USER: [], ROLE: [], DEPARTMENT: [], TEAM: [],
})
const form = reactive({ grantor_type: 'ROLE' as 'USER' | 'ROLE', grantor_id: '', target_type: 'ALL' as Rule['target_type'], target_id: '', action: 'BOTH' as Rule['action'] })

function assignmentTypeLabel(type: string) {
  const labels: Record<string, string> = { USER: 'کاربر', ROLE: 'نقش' }
  return labels[type] || type
}

function targetTypeLabel(type: string) {
  const labels: Record<string, string> = { ALL: 'همه', USER: 'کاربر', ROLE: 'نقش', DEPARTMENT: 'دپارتمان', TEAM: 'تیم' }
  return labels[type] || type
}

function actionLabel(action: string) {
  const labels: Record<string, string> = { BOTH: 'ایجاد و واگذاری', CREATE: 'فقط ایجاد', ASSIGN: 'فقط واگذاری' }
  return labels[action] || action
}
const grantorOptions = computed(() => catalog[form.grantor_type])
const targetOptions = computed(() => (form.target_type === 'ALL' ? [] : catalog[form.target_type]))
const canSubmit = computed(() => !!form.grantor_id && (form.target_type === 'ALL' || !!form.target_id))

watch(() => form.grantor_type, () => { form.grantor_id = '' })
watch(() => form.target_type, () => { form.target_id = '' })

async function list<T>(path: string): Promise<T[]> {
  try {
    return (await apiFetchPage<T>(path, { per_page: 100, include_inactive: false })).items
  }
  catch {
    return []
  }
}

async function loadCatalog() {
  const [users, roles, depts, teams] = await Promise.all([
    list<{ id: number, full_name: string }>('/core/users'),
    list<{ id: number, display_name: string }>('/core/roles'),
    list<{ id: number, name: string }>('/core/departments'),
    list<{ id: number, name: string }>('/core/teams'),
  ])
  catalog.USER = users.map(u => ({ id: u.id, label: u.full_name }))
  catalog.ROLE = roles.map(r => ({ id: r.id, label: r.display_name }))
  catalog.DEPARTMENT = depts.map(d => ({ id: d.id, label: d.name }))
  catalog.TEAM = teams.map(t => ({ id: t.id, label: t.name }))
}

async function load() {
  loading.value = true
  loadError.value = ''
  try {
    rules.value = await apiFetch<Rule[]>('/tasks/assignment-rules')
  }
  catch (err) {
    loadError.value = err instanceof ApiError ? err.message : 'بارگذاری قوانین ناموفق بود.'
  }
  finally {
    loading.value = false
  }
}

async function addRule() {
  saving.value = true
  try {
    await apiFetch('/tasks/assignment-rules', {
      method: 'POST',
      body: {
        grantor_type: form.grantor_type,
        grantor_id: Number(form.grantor_id),
        target_type: form.target_type,
        target_id: form.target_type === 'ALL' ? null : Number(form.target_id),
        action: form.action,
      },
    })
    notify.success('قانون افزوده شد')
    form.grantor_id = ''
    form.target_id = ''
    await load()
  }
  catch (err) {
    notify.error(err instanceof ApiError ? err.message : 'افزودن قانون ناموفق بود')
  }
  finally {
    saving.value = false
  }
}

async function removeRule(r: Rule) {
  try {
    await apiFetch(`/tasks/assignment-rules/${r.id}`, { method: 'DELETE' })
    notify.success('قانون حذف شد')
    await load()
  }
  catch (err) {
    notify.error(err instanceof ApiError ? err.message : 'حذف قانون ناموفق بود')
  }
}

onMounted(async () => {
  // Admin (full access) or an explicit core.permission.update grant may edit.
  canManage.value = auth.hasPermission('core.permission.update')
  await Promise.all([load(), canManage.value ? loadCatalog() : Promise.resolve()])
})
</script>
