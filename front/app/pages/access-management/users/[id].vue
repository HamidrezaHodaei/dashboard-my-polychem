<template>
  <ContainerWrapper
    class="space-y-6 py-6 md:py-8"
    dir="rtl"
  >
    <div class="flex items-center gap-2 text-sm text-muted-foreground">
      <NuxtLink
        to="/access-management/users"
        class="hover:text-foreground"
      >
        کاربران
      </NuxtLink>
      <Icon
        name="lucide:chevron-right"
        class="size-4"
      />
      <span>{{ user?.full_name || '…' }}</span>
    </div>

    <div
      v-if="loading"
      class="p-8 text-center text-sm text-muted-foreground"
    >
      در حال بارگذاری کاربر…
    </div>
    <div
      v-else-if="loadError"
      class="p-8 text-center text-sm text-destructive"
    >
      {{ loadError }}
    </div>

    <template v-else-if="user">
      <!-- Header + actions -->
      <div class="flex flex-col gap-4 border-b pb-6 md:flex-row md:items-center md:justify-between">
        <div class="flex items-center gap-4">
          <Avatar class="size-14">
            <AvatarFallback class="text-lg">
              {{ user.full_name.slice(0, 1) }}
            </AvatarFallback>
          </Avatar>
          <div>
            <div class="flex flex-wrap items-center gap-3">
              <h1 class="text-2xl font-semibold">
                {{ user.full_name }}
              </h1>
              <AccessStatusBadge :status="user.is_active ? 'active' : 'inactive'" />
              <Badge
                v-if="isSelf"
                variant="outline"
              >
                شما
              </Badge>
            </div>
            <p class="mt-1 text-sm text-muted-foreground">
              {{ user.email }} · @{{ user.username }}
            </p>
          </div>
        </div>
        <div class="flex flex-wrap gap-2">
          <Button
            v-if="canUpdate"
            variant="outline"
            class="gap-2"
            @click="openEdit"
          >
            <Icon
              name="lucide:pencil"
              class="size-4"
            /> ویرایش
          </Button>
          <Button
            v-if="canResetPassword"
            variant="outline"
            class="gap-2"
            @click="openPassword"
          >
            <Icon name="lucide:key-round" class="size-4" /> تغییر رمز عبور
          </Button>
          <Button
            v-if="canUpdate"
            variant="outline"
            class="gap-2"
            :disabled="isSelf"
            @click="showToggle = true"
          >
            <Icon
              :name="user.is_active ? 'lucide:user-x' : 'lucide:user-check'"
              class="size-4"
            />
            {{ user.is_active ? 'غیرفعال‌سازی' : 'فعال‌سازی' }}
          </Button>
          <Button
            v-if="canDelete"
            variant="destructive"
            class="gap-2"
            :disabled="isSelf"
            @click="showDelete = true"
          >
            <Icon
              name="lucide:trash-2"
              class="size-4"
            /> حذف
          </Button>
        </div>
      </div>

      <Tabs
        v-model="tab"
        class="space-y-6"
      >
        <TabsList>
          <TabsTrigger value="overview">
            نمای کلی
          </TabsTrigger>
          <TabsTrigger value="roles">
            نقش‌ها
          </TabsTrigger>
          <TabsTrigger value="permissions">
            مجوزها
          </TabsTrigger>
        </TabsList>

        <!-- Overview -->
        <TabsContent
          value="overview"
          class="space-y-6"
        >
          <div class="grid gap-4 sm:grid-cols-3">
            <AccessStat
              label="سازمان"
              :value="orgName(user.organization_id)"
              icon="lucide:building-2"
            />
            <AccessStat
              label="دپارتمان"
              :value="deptName(user.department_id)"
              icon="lucide:users-round"
            />
            <AccessStat
              label="آخرین ورود"
              :value="formatDate(user.last_login_at)"
              icon="lucide:clock-3"
            />
          </div>
          <Card class="overflow-hidden py-0 shadow-none">
            <div class="border-b p-5">
              <h2 class="font-semibold">
                اطلاعات کاربر
              </h2>
            </div>
            <dl class="grid gap-x-6 gap-y-4 p-5 text-sm sm:grid-cols-2">
              <div v-for="row in infoRows" :key="row.label">
                <dt class="text-muted-foreground">
                  {{ row.label }}
                </dt>
                <dd class="mt-0.5 font-medium">
                  {{ row.value }}
                </dd>
              </div>
            </dl>
          </Card>
          <Card class="overflow-hidden py-0 shadow-none">
            <div class="border-b p-5">
              <h2 class="font-semibold">
                نقش‌های تخصیص‌یافته
              </h2>
            </div>
            <div class="flex flex-wrap gap-2 p-5">
              <span
                v-if="!userRoles.length"
                class="text-sm text-muted-foreground"
              >هیچ نقشی تخصیص داده نشده است.</span>
              <Badge
                v-for="ur in userRoles"
                :key="ur.id"
                variant="secondary"
                class="gap-1.5"
              >
                <Icon
                  name="lucide:shield"
                  class="size-3"
                />{{ roleName(ur.role_id) }}
              </Badge>
            </div>
          </Card>
        </TabsContent>

        <!-- Roles -->
        <TabsContent value="roles">
          <Card class="overflow-hidden py-0 shadow-none">
            <div class="flex flex-col gap-3 border-b p-5 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <h2 class="font-semibold">
                  نقش‌ها
                </h2>
                <p class="mt-1 text-sm text-muted-foreground">
                  نقش‌هایی که در حال حاضر به این کاربر اختصاص داده شده‌اند. مجوزهای همهٔ نقش‌ها با یکدیگر ترکیب می‌شوند.
                </p>
              </div>
              <div
                v-if="canUpdate"
                class="flex gap-2"
              >
                <Select v-model="roleToAssign">
                  <SelectTrigger class="w-56">
                    <SelectValue placeholder="انتخاب نقش برای واگذاری" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem
                      v-for="role in assignableRoles"
                      :key="role.id"
                      :value="String(role.id)"
                    >
                      {{ role.display_name }}
                    </SelectItem>
                  </SelectContent>
                </Select>
                <Button
                  variant="outline"
                  size="sm"
                  :disabled="!roleToAssign || assigning"
                  @click="assignSelectedRole"
                >
                  واگذاری
                </Button>
              </div>
            </div>
            <div class="divide-y">
              <div
                v-if="!userRoles.length"
                class="p-5 text-sm text-muted-foreground"
              >
                هیچ نقشی تخصیص داده نشده است.
              </div>
              <div
                v-for="ur in userRoles"
                :key="ur.id"
                class="flex items-center justify-between p-4"
              >
                <div class="flex items-center gap-2">
                  <Icon
                    name="lucide:shield"
                    class="size-4 text-primary"
                  />
                  <NuxtLink
                    :to="`/access-management/roles/${ur.role_id}`"
                    class="font-medium hover:underline"
                  >
                    {{ roleName(ur.role_id) }}
                  </NuxtLink>
                  <span
                    v-if="ur.organization_id"
                    class="text-xs text-muted-foreground"
                  >({{ orgName(ur.organization_id) }})</span>
                </div>
                <Button
                  v-if="canUpdate"
                  variant="ghost"
                  size="sm"
                  class="text-destructive"
                  @click="revoke(ur.role_id)"
                >
                  لغو واگذاری
                </Button>
              </div>
            </div>
          </Card>
        </TabsContent>

        <!-- Permissions -->
        <TabsContent
          value="permissions"
          class="space-y-6"
        >
          <Card class="overflow-hidden py-0 shadow-none">
            <div class="flex flex-col gap-3 border-b p-5 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <h2 class="font-semibold">
                  مجوزهای کاربر
                </h2>
                <p class="mt-1 text-sm text-muted-foreground">
                  دسترسی نهایی این کاربر در هر بخش. انتخاب‌شده یعنی مجاز و انتخاب‌نشده یعنی غیرمجاز. تغییراتی که با نقش‌های کاربر تفاوت داشته باشند، فقط به‌عنوان مجوز مستقیم همین کاربر ذخیره می‌شوند.
                </p>
              </div>
              <div
                v-if="canManagePermissions"
                class="flex items-center gap-2"
              >
                <span
                  v-if="matrix.dirty.value"
                  class="text-xs text-amber-600"
                >{{ matrix.changedCount.value }} تغییر ذخیره‌نشده</span>
                <Button
                  variant="outline"
                  size="sm"
                  :disabled="!matrix.dirty.value || matrix.saving.value"
                  @click="matrix.reset()"
                >
                  بازنشانی
                </Button>
                <Button
                  size="sm"
                  class="gap-2"
                  :disabled="!matrix.dirty.value || matrix.saving.value"
                  @click="savePermissions"
                >
                  <Icon
                    name="lucide:save"
                    class="size-4"
                  /> ذخیرهٔ مجوزها
                </Button>
              </div>
            </div>
            <div
              v-if="isSelf"
              class="border-b bg-amber-500/10 px-5 py-3 text-sm text-amber-700 dark:text-amber-400"
            >
              نمی‌توانید مجوزهای خودتان را تغییر دهید.
            </div>
            <div
              v-if="matrix.loading.value"
              class="p-8 text-center text-sm text-muted-foreground"
            >
              در حال بارگذاری مجوزها…
            </div>
            <div
              v-else-if="matrix.error.value"
              class="p-8 text-center text-sm text-destructive"
            >
              {{ matrix.error.value }}
            </div>
            <AccessPermissionMatrix
              v-else
              v-model="matrix.draft.value"
              :modules="matrix.modules.value"
              :meta="matrix.meta.value"
              mode="user"
              :disabled="!canManagePermissions || isSelf"
            />
            <div class="flex flex-wrap gap-x-5 gap-y-1 border-t px-5 py-3 text-xs text-muted-foreground">
              <span><b class="text-blue-600">نقشی</b> به‌ارث‌رسیده از یک نقش</span>
              <span><b class="text-emerald-600">مستقیم</b> اعطاشده به این کاربر</span>
              <span><b class="text-destructive">ردشده</b> برای این کاربر رد شده است (بر نقش‌ها اولویت دارد)</span>
            </div>
          </Card>

          <Card class="overflow-hidden py-0 shadow-none">
            <div class="border-b p-5">
              <h2 class="font-semibold">
                مجوزهای نهایی
              </h2>
              <p class="mt-1 text-sm text-muted-foreground">
                آنچه در حال حاضر برای این کاربر در سمت سرور اعمال می‌شود (نقش‌ها + مجوزهای مستقیم − موارد ردشده).
              </p>
            </div>
            <div class="space-y-4 p-5">
              <ul class="space-y-1 text-xs text-muted-foreground">
                <li
                  v-for="rule in access?.precedence || []"
                  :key="rule"
                >
                  {{ rule }}
                </li>
              </ul>
              <div
                v-if="!access?.effective.length"
                class="text-sm text-muted-foreground"
              >
                هیچ مجوز مؤثری وجود ندارد.
              </div>
              <div
                v-else
                class="grid gap-2 sm:grid-cols-2 lg:grid-cols-3"
              >
                <div
                  v-for="p in access.effective"
                  :key="p.key"
                  class="flex items-center justify-between gap-2 rounded-md border px-3 py-2"
                >
                  <span class="font-mono text-xs">{{ p.key }}</span>
                  <div class="flex flex-wrap justify-end gap-1">
                    <Badge
                      v-for="(s, i) in p.scopes"
                      :key="i"
                      variant="outline"
                      class="text-[10px]"
                    >
                      {{ permissionSourceLabel(s.source) }} · {{ scopeLabel(s.scope_type) }}{{ s.scope_id ? `:${s.scope_id}` : '' }}
                    </Badge>
                  </div>
                </div>
              </div>

              <div v-if="deniedGrants.length">
                <p class="mb-2 text-sm font-medium">
                  مجوزهای ردشده برای این کاربر
                </p>
                <div class="flex flex-wrap gap-2">
                  <Badge
                    v-for="g in deniedGrants"
                    :key="g.id"
                    variant="destructive"
                    class="font-mono text-[10px]"
                  >
                    {{ g.permission_key }}
                  </Badge>
                </div>
              </div>
            </div>
          </Card>
        </TabsContent>
      </Tabs>
    </template>

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
            <Input v-model="form.full_name" />
          </div>
          <div class="grid grid-cols-2 gap-4">
            <div class="space-y-1.5">
              <Label>ایمیل</Label>
              <Input
                v-model="form.email"
                type="email"
              />
            </div>
            <div class="space-y-1.5">
              <Label>نام کاربری</Label>
              <Input v-model="form.username" />
            </div>
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
                    v-for="d in departmentsForForm"
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
              v-model="form.is_active"
              :disabled="isSelf"
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
            @click="saveProfile"
          >
            ذخیرهٔ تغییرات
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>

    <!-- Set a new password (admin only). Passwords are stored as one-way hashes: the CURRENT password
         can never be read or shown by anyone, so the admin sets a new one and gives it to the user. -->
    <Dialog v-model:open="showPassword">
      <DialogContent dir="rtl" class="sm:max-w-md">
        <DialogHeader class="text-right">
          <DialogTitle>تغییر رمز عبور {{ user?.full_name }}</DialogTitle>
          <DialogDescription>
            رمز فعلی هیچ‌کس قابل مشاهده نیست (فقط به‌صورت رمزنگاری‌شده ذخیره می‌شود)؛ رمز جدیدی تعیین کنید و آن را به کاربر بدهید. کاربر از همه‌ی دستگاه‌ها خارج می‌شود.
          </DialogDescription>
        </DialogHeader>
        <div class="space-y-4">
          <div class="space-y-1.5">
            <Label>رمز عبور جدید</Label>
            <div class="flex gap-2">
              <Input v-model="pwd.value" :type="pwd.visible ? 'text' : 'password'" dir="ltr" class="text-left" autocomplete="new-password" />
              <Button type="button" variant="outline" size="icon" :aria-label="pwd.visible ? 'پنهان‌کردن رمز' : 'نمایش رمز'" @click="pwd.visible = !pwd.visible">
                <Icon :name="pwd.visible ? 'lucide:eye-off' : 'lucide:eye'" class="size-4" />
              </Button>
            </div>
            <p v-if="pwd.error" class="text-xs text-destructive">{{ pwd.error }}</p>
            <p v-else class="text-xs text-muted-foreground">حداقل ۸ نویسه.</p>
          </div>
          <Button type="button" variant="outline" class="w-full gap-2" @click="generatePassword">
            <Icon name="lucide:dices" class="size-4" /> ساخت رمز تصادفی
          </Button>
          <Button v-if="pwd.value" type="button" variant="ghost" class="w-full gap-2" @click="copyPassword">
            <Icon name="lucide:copy" class="size-4" /> کپی رمز
          </Button>
        </div>
        <DialogFooter class="gap-2">
          <Button variant="outline" @click="showPassword = false">انصراف</Button>
          <Button :disabled="pwd.saving" @click="savePassword">{{ pwd.saving ? 'در حال ذخیره...' : 'ذخیره‌ی رمز جدید' }}</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>

    <AccessConfirm
      v-model:open="showToggle"
      :title="user?.is_active ? 'غیرفعال‌سازی کاربر؟' : 'فعال‌سازی کاربر؟'"
      :description="user?.is_active
        ? 'این کاربر دیگر نمی‌تواند وارد سامانه شود. هر زمان بخواهید می‌توانید حساب را دوباره فعال کنید.'
        : 'این کاربر دوباره می‌تواند وارد سامانه شود.'"
      :confirm-label="user?.is_active ? 'غیرفعال‌سازی' : 'فعال‌سازی'"
      :tone="user?.is_active ? 'danger' : 'default'"
      :loading="acting"
      @confirm="toggleActive"
    />
    <AccessConfirm
      v-model:open="showDelete"
      title="حذف کاربر؟"
      description="این کاربر حذف می‌شود و دیگر نمی‌تواند وارد سامانه شود."
      confirm-label="حذف"
      tone="danger"
      :loading="acting"
      @confirm="deleteUser"
    />
  </ContainerWrapper>
</template>

<script setup lang="ts">
const notify = useNotify()
import { ApiError, apiFetch, apiFetchPage } from '~/services/backendApi'
import type { BackendUser } from '~/stores/auth'

interface Role { id: number, name: string, display_name: string, is_active: boolean }
interface UserRole { id: number, user_id: number, role_id: number, organization_id: number | null }
interface Named { id: number, name: string, organization_id?: number }
interface Access {
  effective: { key: string, scopes: { scope_type: string, scope_id: number | null, source: string }[] }[]
  direct_grants: { id: number, permission_key: string, scope_type: string, scope_id: number | null, effect: 'ALLOW' | 'DENY' }[]
  precedence: string[]
}

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const userId = Number(route.params.id)

const tab = ref(['overview', 'roles', 'permissions'].includes(String(route.query.tab)) ? String(route.query.tab) : 'overview')
watch(tab, v => router.replace({ query: { ...route.query, tab: v } }))
watch(() => route.query.tab, (v) => {
  if (['overview', 'roles', 'permissions'].includes(String(v)) && v !== tab.value) tab.value = String(v)
})

const user = ref<BackendUser | null>(null)
const userRoles = ref<UserRole[]>([])
const allRoles = ref<Role[]>([])
const organizations = ref<Named[]>([])
const departments = ref<Named[]>([])
const access = ref<Access | null>(null)
const loading = ref(true)
const loadError = ref('')
const saving = ref(false)
const acting = ref(false)
const assigning = ref(false)
const roleToAssign = ref<string>('')

const isSelf = computed(() => user.value?.id === auth.user?.id)
const canUpdate = computed(() => auth.hasPermission('core.user.update'))
// Shown to the admin (and to anyone who may edit users, so the control can never silently vanish if the
// session payload lacks the role list); the server still answers 403 unless the caller is an admin.
const canResetPassword = computed(() => auth.isAdmin || canUpdate.value)
const canDelete = computed(() => auth.hasPermission('core.user.delete'))
const canManagePermissions = computed(() => canUpdate.value && auth.hasPermission('core.permission.update'))

const matrix = usePermissionMatrix(`/core/users/${userId}`, 'user')

function scopeLabel(scope: string) {
  const labels: Record<string, string> = { GLOBAL: 'سراسری', ORGANIZATION: 'سازمان', DEPARTMENT: 'دپارتمان', TEAM: 'تیم', SELF: 'خود کاربر' }
  return labels[scope] || scope
}

function permissionSourceLabel(source: string) {
  const labels: Record<string, string> = { ROLE: 'نقش', DIRECT: 'مستقیم', DENY: 'ردشده' }
  return labels[source] || source
}

const deniedGrants = computed(() => (access.value?.direct_grants || []).filter(g => g.effect === 'DENY'))
const assignableRoles = computed(() =>
  allRoles.value.filter(r => r.is_active && !userRoles.value.some(ur => ur.role_id === r.id)),
)

const infoRows = computed(() => !user.value
  ? []
  : [
      { label: 'شناسهٔ کاربر', value: `#${user.value.id}` },
      { label: 'نام کامل', value: user.value.full_name },
      { label: 'ایمیل', value: user.value.email },
      { label: 'نام کاربری', value: user.value.username },
      { label: 'سازمان', value: orgName(user.value.organization_id) },
      { label: 'دپارتمان', value: deptName(user.value.department_id) },
      { label: 'وضعیت', value: user.value.is_active ? 'فعال' : 'غیرفعال' },
      { label: 'آخرین ورود', value: formatDate(user.value.last_login_at) },
      { label: 'ایجادشده در', value: formatDate(user.value.created_at) },
      { label: 'به‌روزرسانی‌شده در', value: formatDate(user.value.updated_at) },
    ])

function roleName(roleId: number) {
  return allRoles.value.find(r => r.id === roleId)?.display_name || `نقش #${roleId}`
}
function orgName(id: number | null) {
  if (!id) return '—'
  return organizations.value.find(o => o.id === id)?.name || `#${id}`
}
function deptName(id: number | null) {
  if (!id) return '—'
  return departments.value.find(d => d.id === id)?.name || `#${id}`
}
function formatDate(value: string | null) {
  if (!value) return 'هرگز'
  return new Date(value).toLocaleString()
}

async function loadAccess() {
  try {
    access.value = await apiFetch<Access>(`/core/users/${userId}/access`)
  }
  catch {
    access.value = null
  }
}

async function loadAll() {
  loading.value = true
  loadError.value = ''
  try {
    const [fetchedUser, roles, roleAssignments, orgs, depts] = await Promise.all([
      apiFetch<BackendUser>(`/core/users/${userId}`),
      apiFetchPage<Role>('/core/roles', { per_page: 100, include_inactive: true }).catch(() => ({ items: [] as Role[] })),
      apiFetch<UserRole[]>(`/core/users/${userId}/roles`),
      apiFetchPage<Named>('/core/organizations', { per_page: 100 }).catch(() => ({ items: [] as Named[] })),
      apiFetchPage<Named>('/core/departments', { per_page: 100 }).catch(() => ({ items: [] as Named[] })),
    ])
    user.value = fetchedUser
    allRoles.value = roles.items
    userRoles.value = roleAssignments
    organizations.value = orgs.items
    departments.value = depts.items
  }
  catch (err) {
    loadError.value = err instanceof ApiError ? err.message : 'بارگذاری کاربر ناموفق بود.'
  }
  finally {
    loading.value = false
  }
  if (user.value) {
    await Promise.all([loadAccess(), matrix.load().catch(() => {})])
  }
}

// ---- edit profile
const showEdit = ref(false)
const form = reactive({
  full_name: '',
  email: '',
  username: '',
  organization_id: 'none' as string,
  department_id: 'none' as string,
  is_active: true,
})
const departmentsForForm = computed(() =>
  form.organization_id === 'none'
    ? departments.value
    : departments.value.filter(d => String(d.organization_id) === form.organization_id),
)

function openEdit() {
  if (!user.value) return
  Object.assign(form, {
    full_name: user.value.full_name,
    email: user.value.email,
    username: user.value.username,
    organization_id: user.value.organization_id ? String(user.value.organization_id) : 'none',
    department_id: user.value.department_id ? String(user.value.department_id) : 'none',
    is_active: user.value.is_active,
  })
  showEdit.value = true
}

async function saveProfile() {
  saving.value = true
  try {
    user.value = await apiFetch<BackendUser>(`/core/users/${userId}`, {
      method: 'PATCH',
      body: {
        full_name: form.full_name,
        email: form.email,
        username: form.username,
        organization_id: form.organization_id === 'none' ? null : Number(form.organization_id),
        department_id: form.department_id === 'none' ? null : Number(form.department_id),
        is_active: form.is_active,
      },
    })
    showEdit.value = false
    notify.success('کاربر به‌روزرسانی شد')
    // Placement affects scope-based access, so refresh the merged view.
    await Promise.all([loadAccess(), matrix.load().catch(() => {})])
  }
  catch (err) {
    notify.error(err instanceof ApiError ? err.message : 'ذخیرهٔ کاربر ناموفق بود')
  }
  finally {
    saving.value = false
  }
}

// ---- activate / delete
const showPassword = ref(false)
const pwd = reactive({ value: '', visible: false, saving: false, error: '' })
function openPassword() {
  Object.assign(pwd, { value: '', visible: false, saving: false, error: '' })
  showPassword.value = true
}
function generatePassword() {
  // 14 characters from an unambiguous set (no 0/O, 1/l/I), using the browser's secure random source
  const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789@#$%'
  const bytes = crypto.getRandomValues(new Uint8Array(14))
  pwd.value = Array.from(bytes, b => chars[b % chars.length]).join('')
  pwd.visible = true
  pwd.error = ''
}
async function copyPassword() {
  try {
    await navigator.clipboard.writeText(pwd.value)
    notify.success('رمز کپی شد')
  }
  catch {
    notify.error('کپی انجام نشد؛ رمز را دستی کپی کنید')
  }
}
async function savePassword() {
  if (pwd.value.length < 8) {
    pwd.error = 'رمز عبور باید حداقل ۸ نویسه باشد.'
    return
  }
  pwd.saving = true
  try {
    await apiFetch(`/core/users/${userId}/password`, { method: 'POST', body: { new_password: pwd.value } })
    showPassword.value = false
    notify.success('رمز عبور جدید ذخیره شد و کاربر از دستگاه‌ها خارج شد')
  }
  catch (err) {
    notify.error(err instanceof ApiError && err.status === 403 ? 'فقط مدیر سیستم می‌تواند رمز کاربران را تغییر دهد' : err instanceof ApiError ? err.message : 'ذخیره‌ی رمز ناموفق بود')
  }
  finally {
    pwd.saving = false
  }
}

const showToggle = ref(false)
const showDelete = ref(false)

async function toggleActive() {
  if (!user.value) return
  acting.value = true
  try {
    const next = !user.value.is_active
    user.value = await apiFetch<BackendUser>(`/core/users/${userId}`, { method: 'PATCH', body: { is_active: next } })
    showToggle.value = false
    notify.success(next ? 'کاربر فعال شد' : 'کاربر غیرفعال شد')
  }
  catch (err) {
    notify.error(err instanceof ApiError ? err.message : 'تغییر وضعیت ناموفق بود')
  }
  finally {
    acting.value = false
  }
}

async function deleteUser() {
  acting.value = true
  try {
    await apiFetch(`/core/users/${userId}`, { method: 'DELETE' })
    notify.success('کاربر حذف شد')
    await navigateTo('/access-management/users')
  }
  catch (err) {
    notify.error(err instanceof ApiError ? err.message : 'حذف کاربر ناموفق بود')
  }
  finally {
    acting.value = false
  }
}

// ---- roles
async function afterRoleChange() {
  // Roles change the merged permissions -> refresh both views.
  await Promise.all([loadAccess(), matrix.load().catch(() => {})])
}

async function assignSelectedRole() {
  if (!roleToAssign.value) return
  assigning.value = true
  try {
    const created = await apiFetch<UserRole>(`/core/users/${userId}/roles`, {
      method: 'POST',
      body: { role_id: Number(roleToAssign.value) },
    })
    userRoles.value.push(created)
    roleToAssign.value = ''
    notify.success('نقش واگذار شد')
    await afterRoleChange()
  }
  catch (err) {
    notify.error(err instanceof ApiError ? err.message : 'واگذاری نقش ناموفق بود')
  }
  finally {
    assigning.value = false
  }
}

async function revoke(roleId: number) {
  try {
    await apiFetch(`/core/users/${userId}/roles/${roleId}`, { method: 'DELETE' })
    userRoles.value = userRoles.value.filter(ur => ur.role_id !== roleId)
    notify.success('نقش لغو شد')
    await afterRoleChange()
  }
  catch (err) {
    notify.error(err instanceof ApiError ? err.message : 'لغو نقش ناموفق بود')
  }
}

// ---- permissions
async function savePermissions() {
  try {
    await matrix.save()
    notify.success('مجوزها ذخیره شدند')
    await loadAccess()
  }
  catch (err) {
    notify.error(err instanceof ApiError ? err.message : 'ذخیرهٔ مجوزها ناموفق بود')
  }
}

onMounted(async () => {
  await loadAll()
  // deep link from the users list («تغییر رمز عبور»)
  if (route.query.password && user.value && canResetPassword.value) openPassword()
})
usePageSeoMeta({ title: () => user.value?.full_name || 'کاربر' })
</script>
