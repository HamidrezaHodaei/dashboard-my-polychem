<template>
  <ContainerWrapper
    class="space-y-6 py-6 md:py-8"
    dir="rtl"
  >
    <AccessPageHeader
      title="کاربران"
      description="مدیریت کاربران، نقش‌ها و مجوزهای اختصاصی هر کاربر"
      action-label="افزودن کاربر"
      @action="openCreate"
    />
    <div class="grid gap-4 sm:grid-cols-3">
      <AccessStat
        label="تعداد کل کاربران"
        :value="total"
        icon="lucide:users"
      />
      <AccessStat
        label="فعال در این صفحه"
        :value="activeCount"
        icon="lucide:user-check"
      />
      <AccessStat
        label="غیرفعال در این صفحه"
        :value="users.length - activeCount"
        icon="lucide:user-x"
      />
    </div>
    <Card class="overflow-hidden py-0 shadow-none">
      <div class="flex flex-col gap-3 border-b p-4 sm:flex-row sm:items-center sm:justify-between">
        <div class="flex w-full flex-col gap-3 sm:flex-row sm:items-center">
          <div class="relative w-full sm:max-w-sm">
            <Icon
              name="lucide:search"
              class="absolute left-3 top-2.5 size-4 text-muted-foreground"
            />
            <Input
              v-model="query"
              placeholder="جستجو بر اساس نام، ایمیل یا نام کاربری"
              class="pl-9"
            />
          </div>
          <Select v-model="statusFilter">
            <SelectTrigger class="w-full sm:w-40">
              <SelectValue placeholder="وضعیت" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">
                همهٔ وضعیت‌ها
              </SelectItem>
              <SelectItem value="active">
                فعال
              </SelectItem>
              <SelectItem value="inactive">
                غیرفعال
              </SelectItem>
            </SelectContent>
          </Select>
        </div>
        <Button
          variant="outline"
          class="gap-2"
          :disabled="loading"
          @click="load"
        >
          <Icon
            name="lucide:refresh-cw"
            class="size-4"
          /> بازآوری
        </Button>
      </div>
      <div class="overflow-x-auto">
        <div
          v-if="loading && !users.length"
          class="p-8 text-center text-sm text-muted-foreground"
        >
          در حال بارگذاری کاربران…
        </div>
        <div
          v-else-if="loadError"
          class="p-8 text-center text-sm text-destructive"
        >
          {{ loadError }}
        </div>
        <Table v-else-if="visibleUsers.length">
          <TableHeader>
            <TableRow>
              <TableHead>کاربر</TableHead>
              <TableHead>نام کاربری</TableHead>
              <TableHead>سازمان / دپارتمان</TableHead>
              <TableHead>آخرین ورود</TableHead>
              <TableHead>وضعیت</TableHead>
              <TableHead class="text-right">
                عملیات
              </TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            <TableRow
              v-for="user in visibleUsers"
              :key="user.id"
              class="group"
            >
              <TableCell>
                <NuxtLink
                  :to="`/access-management/users/${user.id}`"
                  class="flex items-center gap-3"
                >
                  <Avatar class="size-9">
                    <AvatarFallback>{{ user.full_name.slice(0, 1) }}</AvatarFallback>
                  </Avatar>
                  <div>
                    <p class="font-medium hover:underline">
                      {{ user.full_name }}
                    </p>
                    <p class="text-xs text-muted-foreground">
                      {{ user.email }}
                    </p>
                  </div>
                </NuxtLink>
              </TableCell>
              <TableCell>
                <Badge variant="outline">
                  {{ user.username }}
                </Badge>
              </TableCell>
              <TableCell>
                <p>{{ orgName(user.organization_id) }}</p>
                <p class="text-xs text-muted-foreground">
                  {{ deptName(user.department_id) }}
                </p>
              </TableCell>
              <TableCell class="text-muted-foreground">
                {{ formatDate(user.last_login_at) }}
              </TableCell>
              <TableCell><AccessStatusBadge :status="user.is_active ? 'active' : 'inactive'" /></TableCell>
              <TableCell>
                <div class="flex justify-end gap-1">
                  <Button
                    variant="ghost"
                    size="icon"
                    title="مشاهدهٔ جزئیات"
                    as-child
                  >
                    <NuxtLink :to="`/access-management/users/${user.id}`">
                      <Icon
                        name="lucide:eye"
                        class="size-4"
                      />
                    </NuxtLink>
                  </Button>
                  <Button
                    v-if="auth.hasPermission('core.user.update')"
                    variant="ghost"
                    size="icon"
                    title="ویرایش"
                    @click="openEdit(user)"
                  >
                    <Icon
                      name="lucide:pencil"
                      class="size-4"
                    />
                  </Button>
                  <Button
                    variant="ghost"
                    size="icon"
                    title="مجوزها"
                    as-child
                  >
                    <NuxtLink :to="`/access-management/users/${user.id}?tab=permissions`">
                      <Icon
                        name="lucide:key-round"
                        class="size-4"
                      />
                    </NuxtLink>
                  </Button>
                  <Button
                    v-if="auth.isAdmin || auth.hasPermission('core.user.update')"
                    variant="ghost"
                    size="icon"
                    title="تغییر رمز عبور"
                    as-child
                  >
                    <NuxtLink :to="`/access-management/users/${user.id}?password=1`">
                      <Icon
                        name="lucide:lock-keyhole"
                        class="size-4"
                      />
                    </NuxtLink>
                  </Button>
                  <Button
                    v-if="auth.hasPermission('core.user.update')"
                    variant="ghost"
                    size="icon"
                    :title="user.is_active ? 'غیرفعال‌سازی' : 'فعال‌سازی'"
                    :disabled="isSelf(user)"
                    @click="askToggle(user)"
                  >
                    <Icon
                      :name="user.is_active ? 'lucide:user-x' : 'lucide:user-check'"
                      class="size-4"
                    />
                  </Button>
                  <Button
                    v-if="auth.hasPermission('core.user.delete')"
                    variant="ghost"
                    size="icon"
                    title="حذف"
                    class="text-destructive"
                    :disabled="isSelf(user)"
                    @click="askDelete(user)"
                  >
                    <Icon
                      name="lucide:trash-2"
                      class="size-4"
                    />
                  </Button>
                </div>
              </TableCell>
            </TableRow>
          </TableBody>
        </Table>
        <AccessEmptyState v-else />
      </div>
      <div class="flex items-center justify-between border-t p-4 text-sm text-muted-foreground">
        <span>نمایش {{ visibleUsers.length }} مورد از {{ total }} کاربر · صفحهٔ {{ page }} از {{ totalPages }}</span>
        <div class="flex gap-1">
          <Button
            variant="outline"
            size="icon"
            :disabled="page <= 1 || loading"
            @click="page--; load()"
          >
            <Icon
              name="lucide:chevron-left"
              class="size-4"
            />
          </Button>
          <Button
            variant="outline"
            size="icon"
            :disabled="page >= totalPages || loading"
            @click="page++; load()"
          >
            <Icon
              name="lucide:chevron-right"
              class="size-4"
            />
          </Button>
        </div>
      </div>
    </Card>

    <!-- Create -->
    <Dialog v-model:open="showCreate">
      <DialogContent>
        <DialogHeader>
          <DialogTitle>افزودن کاربر</DialogTitle>
          <DialogDescription>ایجاد حساب کاربری جدید.</DialogDescription>
        </DialogHeader>
        <div class="space-y-4">
          <div class="space-y-1.5">
            <Label>نام کامل</Label>
            <Input
              v-model="form.full_name"
              placeholder="نام کامل"
            />
          </div>
          <div class="grid grid-cols-2 gap-4">
            <div class="space-y-1.5">
              <Label>ایمیل</Label>
              <Input
                v-model="form.email"
                type="email"
                placeholder="ایمیل کاربر"
              />
            </div>
            <div class="space-y-1.5">
              <Label>نام کاربری</Label>
              <Input
                v-model="form.username"
                placeholder="نام کاربری"
              />
            </div>
          </div>
          <div class="space-y-1.5">
            <Label>رمز عبور</Label>
            <Input
              v-model="form.password"
              type="password"
              placeholder="حداقل ۸ نویسه"
            />
          </div>
          <div class="grid grid-cols-2 gap-4">
            <div class="space-y-1.5">
              <Label>سازمان</Label>
              <Select v-model="form.organization_id">
                <SelectTrigger class="w-full">
                  <SelectValue placeholder="بدون مورد" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">
                    بدون مورد
                  </SelectItem>
                  <SelectItem
                    v-for="o in organizations"
                    :key="o.id"
                    :value="String(o.id)"
                  >
                    {{ o.name }}
                  </SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div class="space-y-1.5">
              <Label>دپارتمان</Label>
              <Select v-model="form.department_id">
                <SelectTrigger class="w-full">
                  <SelectValue placeholder="بدون مورد" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">
                    بدون مورد
                  </SelectItem>
                  <SelectItem
                    v-for="d in departmentsFor(form.organization_id)"
                    :key="d.id"
                    :value="String(d.id)"
                  >
                    {{ d.name }}
                  </SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </div>
        <DialogFooter>
          <Button
            variant="outline"
            @click="showCreate = false"
          >
            انصراف
          </Button>
          <Button
            :disabled="creating"
            @click="createUser"
          >
            ایجاد
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>

    <!-- Edit -->
    <Dialog v-model:open="showEdit">
      <DialogContent>
        <DialogHeader>
          <DialogTitle>ویرایش کاربر</DialogTitle>
          <DialogDescription>به‌روزرسانی نمایه و جایگاه سازمانی.</DialogDescription>
        </DialogHeader>
        <div class="space-y-4">
          <div class="space-y-1.5">
            <Label>نام کامل</Label>
            <Input v-model="editForm.full_name" />
          </div>
          <div class="grid grid-cols-2 gap-4">
            <div class="space-y-1.5">
              <Label>ایمیل</Label>
              <Input
                v-model="editForm.email"
                type="email"
              />
            </div>
            <div class="space-y-1.5">
              <Label>نام کاربری</Label>
              <Input v-model="editForm.username" />
            </div>
          </div>
          <div class="grid grid-cols-2 gap-4">
            <div class="space-y-1.5">
              <Label>سازمان</Label>
              <Select v-model="editForm.organization_id">
                <SelectTrigger class="w-full">
                  <SelectValue placeholder="بدون مورد" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">
                    بدون مورد
                  </SelectItem>
                  <SelectItem
                    v-for="o in organizations"
                    :key="o.id"
                    :value="String(o.id)"
                  >
                    {{ o.name }}
                  </SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div class="space-y-1.5">
              <Label>دپارتمان</Label>
              <Select v-model="editForm.department_id">
                <SelectTrigger class="w-full">
                  <SelectValue placeholder="بدون مورد" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">
                    بدون مورد
                  </SelectItem>
                  <SelectItem
                    v-for="d in departmentsFor(editForm.organization_id)"
                    :key="d.id"
                    :value="String(d.id)"
                  >
                    {{ d.name }}
                  </SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          <div class="flex items-center gap-2">
            <Switch
              v-model="editForm.is_active"
              :disabled="editing ? isSelf(editing) : false"
            />
            <Label>فعال</Label>
          </div>
        </div>
        <DialogFooter>
          <Button
            variant="outline"
            @click="showEdit = false"
          >
            انصراف
          </Button>
          <Button
            :disabled="saving"
            @click="saveEdit"
          >
            ذخیرهٔ تغییرات
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>

    <!-- Activate / deactivate -->
    <AccessConfirm
      v-model:open="showToggle"
      :title="target?.is_active ? 'غیرفعال‌سازی کاربر؟' : 'فعال‌سازی کاربر؟'"
      :description="target?.is_active
        ? `${target?.full_name} دیگر نمی‌تواند وارد سامانه شود. هر زمان بخواهید می‌توانید حساب را دوباره فعال کنید.`
        : `${target?.full_name} دوباره می‌تواند وارد سامانه شود.`"
      :confirm-label="target?.is_active ? 'غیرفعال‌سازی' : 'فعال‌سازی'"
      :tone="target?.is_active ? 'danger' : 'default'"
      :loading="acting"
      @confirm="confirmToggle"
    />

    <!-- Delete -->
    <AccessConfirm
      v-model:open="showDelete"
      title="حذف کاربر؟"
      :description="`${target?.full_name} حذف می‌شود و دیگر نمی‌تواند وارد سامانه شود. این عملیات از طریق رابط کاربری قابل بازگشت نیست.`"
      confirm-label="حذف"
      tone="danger"
      :loading="acting"
      @confirm="confirmDelete"
    />
  </ContainerWrapper>
</template>

<script setup lang="ts">
const notify = useNotify()
import { ApiError, apiFetch, apiFetchPage } from '~/services/backendApi'
import type { BackendUser } from '~/stores/auth'

interface Organization { id: number, name: string }
interface Department { id: number, name: string, organization_id: number }

const auth = useAuthStore()

const query = ref('')
const statusFilter = ref('all')
const page = ref(1)
const perPage = 20
const total = ref(0)
const users = ref<BackendUser[]>([])
const organizations = ref<Organization[]>([])
const departments = ref<Department[]>([])
const loading = ref(false)
const loadError = ref('')

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / perPage)))
const activeCount = computed(() => users.value.filter(u => u.is_active).length)
const visibleUsers = computed(() => {
  if (statusFilter.value === 'active') return users.value.filter(u => u.is_active)
  if (statusFilter.value === 'inactive') return users.value.filter(u => !u.is_active)
  return users.value
})

const isSelf = (u: BackendUser | null) => !!u && u.id === auth.user?.id

function orgName(id: number | null) {
  if (!id) return '—'
  return organizations.value.find(o => o.id === id)?.name || `#${id}`
}
function deptName(id: number | null) {
  if (!id) return '—'
  return departments.value.find(d => d.id === id)?.name || `#${id}`
}
function departmentsFor(orgId: string) {
  if (orgId === 'none') return departments.value
  return departments.value.filter(d => String(d.organization_id) === orgId)
}
function formatDate(value: string | null) {
  if (!value) return 'هرگز'
  return new Date(value).toLocaleString()
}

async function load() {
  loading.value = true
  loadError.value = ''
  try {
    const [result, orgs, depts] = await Promise.all([
      apiFetchPage<BackendUser>('/core/users', {
        page: page.value,
        per_page: perPage,
        include_inactive: true,
        q: query.value.trim() || undefined,
      }),
      apiFetchPage<Organization>('/core/organizations', { per_page: 100 }),
      apiFetchPage<Department>('/core/departments', { per_page: 100 }),
    ])
    users.value = result.items
    total.value = result.total
    organizations.value = orgs.items
    departments.value = depts.items
  }
  catch (err) {
    loadError.value = err instanceof ApiError ? err.message : 'بارگذاری کاربران ناموفق بود.'
  }
  finally {
    loading.value = false
  }
}

let searchTimer: ReturnType<typeof setTimeout> | undefined
watch(query, () => {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    page.value = 1
    load()
  }, 300)
})

// ---- create
const showCreate = ref(false)
const creating = ref(false)
const form = reactive({
  full_name: '',
  email: '',
  username: '',
  password: '',
  organization_id: 'none' as string,
  department_id: 'none' as string,
})

function openCreate() {
  Object.assign(form, { full_name: '', email: '', username: '', password: '', organization_id: 'none', department_id: 'none' })
  showCreate.value = true
}

async function createUser() {
  creating.value = true
  try {
    await apiFetch('/core/users', {
      method: 'POST',
      body: {
        full_name: form.full_name,
        email: form.email,
        username: form.username,
        password: form.password,
        organization_id: form.organization_id === 'none' ? null : Number(form.organization_id),
        department_id: form.department_id === 'none' ? null : Number(form.department_id),
      },
    })
    notify.success('کاربر ایجاد شد')
    showCreate.value = false
    await load()
  }
  catch (err) {
    notify.error(err instanceof ApiError ? err.message : 'ایجاد کاربر ناموفق بود')
  }
  finally {
    creating.value = false
  }
}

// ---- edit
const showEdit = ref(false)
const saving = ref(false)
const editing = ref<BackendUser | null>(null)
const editForm = reactive({
  full_name: '',
  email: '',
  username: '',
  organization_id: 'none' as string,
  department_id: 'none' as string,
  is_active: true,
})

function openEdit(user: BackendUser) {
  editing.value = user
  Object.assign(editForm, {
    full_name: user.full_name,
    email: user.email,
    username: user.username,
    organization_id: user.organization_id ? String(user.organization_id) : 'none',
    department_id: user.department_id ? String(user.department_id) : 'none',
    is_active: user.is_active,
  })
  showEdit.value = true
}

async function saveEdit() {
  if (!editing.value) return
  saving.value = true
  try {
    await apiFetch(`/core/users/${editing.value.id}`, {
      method: 'PATCH',
      body: {
        full_name: editForm.full_name,
        email: editForm.email,
        username: editForm.username,
        organization_id: editForm.organization_id === 'none' ? null : Number(editForm.organization_id),
        department_id: editForm.department_id === 'none' ? null : Number(editForm.department_id),
        is_active: editForm.is_active,
      },
    })
    notify.success('کاربر به‌روزرسانی شد')
    showEdit.value = false
    await load()
  }
  catch (err) {
    notify.error(err instanceof ApiError ? err.message : 'به‌روزرسانی کاربر ناموفق بود')
  }
  finally {
    saving.value = false
  }
}

// ---- activate / deactivate / delete
const target = ref<BackendUser | null>(null)
const showToggle = ref(false)
const showDelete = ref(false)
const acting = ref(false)

function askToggle(user: BackendUser) {
  target.value = user
  showToggle.value = true
}
function askDelete(user: BackendUser) {
  target.value = user
  showDelete.value = true
}

async function confirmToggle() {
  if (!target.value) return
  acting.value = true
  try {
    const next = !target.value.is_active
    await apiFetch(`/core/users/${target.value.id}`, { method: 'PATCH', body: { is_active: next } })
    notify.success(next ? 'کاربر فعال شد' : 'کاربر غیرفعال شد')
    showToggle.value = false
    await load()
  }
  catch (err) {
    notify.error(err instanceof ApiError ? err.message : 'تغییر وضعیت ناموفق بود')
  }
  finally {
    acting.value = false
  }
}

async function confirmDelete() {
  if (!target.value) return
  acting.value = true
  try {
    await apiFetch(`/core/users/${target.value.id}`, { method: 'DELETE' })
    notify.success('کاربر حذف شد')
    showDelete.value = false
    if (users.value.length === 1 && page.value > 1) page.value--
    await load()
  }
  catch (err) {
    notify.error(err instanceof ApiError ? err.message : 'حذف کاربر ناموفق بود')
  }
  finally {
    acting.value = false
  }
}

onMounted(load)
usePageSeoMeta({ title: 'کاربران' })
</script>
