<template>
  <ContainerWrapper
    class="space-y-6 py-6 md:py-8"
    dir="rtl"
  >
    <div class="flex items-center gap-2 text-sm text-muted-foreground">
      <NuxtLink
        to="/access-management/roles"
        class="hover:text-foreground"
      >
        نقش‌ها
      </NuxtLink>
      <Icon
        name="lucide:chevron-right"
        class="size-4"
      />
      <span>{{ role?.display_name || '…' }}</span>
    </div>

    <div
      v-if="loading"
      class="p-8 text-center text-sm text-muted-foreground"
    >
      در حال بارگذاری نقش…
    </div>
    <div
      v-else-if="loadError"
      class="p-8 text-center text-sm text-destructive"
    >
      {{ loadError }}
    </div>

    <template v-else-if="role">
      <div class="flex flex-col gap-2 border-b pb-6 md:flex-row md:items-center md:justify-between">
        <div>
          <div class="flex items-center gap-3">
            <h1 class="text-2xl font-semibold">
              {{ role.display_name }}
            </h1>
            <AccessStatusBadge :status="role.is_active ? 'active' : 'inactive'" />
            <Badge
              v-if="role.is_system_role"
              variant="outline"
            >
              سیستمی
            </Badge>
          </div>
          <p class="mt-1 text-sm text-muted-foreground">
            {{ role.name }} · {{ role.description || 'بدون توضیحات' }}
          </p>
        </div>
      </div>

      <Tabs
        v-model="tab"
        class="space-y-6"
      >
        <TabsList>
          <TabsTrigger value="matrix">
            ماتریس مجوزها
          </TabsTrigger>
          <TabsTrigger value="advanced">
            مجوزهای محدود به دامنه (پیشرفته)
          </TabsTrigger>
        </TabsList>

        <TabsContent value="matrix">
          <Card class="overflow-hidden py-0 shadow-none">
            <div class="flex flex-col gap-3 border-b p-5 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <h2 class="font-semibold">
                  مجوزهای نقش
                </h2>
                <p class="mt-1 text-sm text-muted-foreground">
                  این نقش مشخص می‌کند کاربران در هر بخش چه کارهایی می‌توانند انجام دهند. کاربران می‌توانند در صفحهٔ خود مجوزهای مستقیم یا منع دسترسی نیز دریافت کنند.
                </p>
              </div>
              <div
                v-if="canUpdate"
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
                  @click="saveMatrix"
                >
                  <Icon
                    name="lucide:save"
                    class="size-4"
                  /> ذخیرهٔ مجوزها
                </Button>
              </div>
            </div>
            <div
              v-if="role.name === 'admin'"
              class="border-b bg-amber-500/10 px-5 py-3 text-sm text-amber-700 dark:text-amber-400"
            >
              نقش مدیر همیشه دسترسی کامل دارد و نمی‌توان مجوزهای آن را کاهش داد.
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
              mode="role"
              :disabled="!canUpdate || role.name === 'admin'"
            />
          </Card>
        </TabsContent>

        <TabsContent value="advanced">
          <Card class="overflow-hidden py-0 shadow-none">
            <div class="flex flex-col gap-3 border-b p-5 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <h2 class="font-semibold">
                  اعطای مجوزها
                </h2>
                <p class="mt-1 text-sm text-muted-foreground">
                  مجوزهایی که این نقش در یک دامنهٔ مشخص دارد.
                </p>
              </div>
              <div class="flex flex-wrap gap-2">
                <Select v-model="newGrant.permission_id">
                  <SelectTrigger class="w-56">
                    <SelectValue placeholder="انتخاب مجوز" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem
                      v-for="p in allPermissions"
                      :key="p.id"
                      :value="String(p.id)"
                    >
                      {{ p.key }}
                    </SelectItem>
                  </SelectContent>
                </Select>
                <Select v-model="newGrant.scope_type">
                  <SelectTrigger class="w-36">
                    <SelectValue placeholder="دامنه" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="GLOBAL">سراسری
                    </SelectItem>
                    <SelectItem value="ORGANIZATION">سازمان
                    </SelectItem>
                    <SelectItem value="DEPARTMENT">دپارتمان
                    </SelectItem>
                    <SelectItem value="TEAM">تیم
                    </SelectItem>
                    <SelectItem value="SELF">خود کاربر
                    </SelectItem>
                  </SelectContent>
                </Select>
                <Input
                  v-if="needsScopeId"
                  v-model="newGrant.scope_id"
                  type="number"
                  placeholder="شناسهٔ دامنه"
                  class="w-28"
                />
                <Button
                  size="sm"
                  :disabled="!canGrant || granting"
                  @click="addGrant"
                >
                  اعطای مجوز
                </Button>
              </div>
            </div>
            <div class="divide-y">
              <div
                v-if="!grants.length"
                class="p-5 text-sm text-muted-foreground"
              >
                هنوز مجوزی اعطا نشده است.
              </div>
              <div
                v-for="grant in grants"
                :key="grant.id"
                class="flex items-center justify-between p-4"
              >
                <div class="flex items-center gap-2">
                  <Icon
                    name="lucide:key"
                    class="size-4 text-primary"
                  />
                  <span class="font-medium">{{ permissionKey(grant.permission_id) }}</span>
                  <Badge variant="outline">
                    {{ scopeLabel(grant.scope_type) }}{{ grant.scope_id ? `:${grant.scope_id}` : '' }}
                  </Badge>
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  class="text-destructive"
                  @click="revoke(grant)"
                >
                  لغو مجوز
                </Button>
              </div>
            </div>
          </Card>
        </TabsContent>
      </Tabs>
    </template>
  </ContainerWrapper>
</template>

<script setup lang="ts">
const notify = useNotify()
import { ApiError, apiFetch, apiFetchPage } from '~/services/backendApi'

interface Role { id: number, name: string, display_name: string, description: string | null, is_system_role: boolean, is_active: boolean }
interface Permission { id: number, key: string }
interface Grant { id: number, role_id: number, permission_id: number, scope_type: string, scope_id: number | null }

const route = useRoute()
const roleId = Number(route.params.id)
const auth = useAuthStore()
const tab = ref(['matrix', 'advanced'].includes(String(route.query.tab)) ? String(route.query.tab) : 'matrix')
const canUpdate = computed(() => auth.hasPermission('core.role.update'))
const matrix = usePermissionMatrix(`/core/roles/${roleId}`, 'role')

async function saveMatrix() {
  try {
    await matrix.save()
    notify.success('مجوزهای نقش ذخیره شدند')
    await reloadGrants()
  }
  catch (err) {
    notify.error(err instanceof ApiError ? err.message : 'ذخیرهٔ مجوزهای نقش ناموفق بود')
  }
}

async function reloadGrants() {
  try {
    grants.value = await apiFetch<Grant[]>(`/core/roles/${roleId}/permissions`)
  }
  catch {
    // non-fatal: the matrix is the source of truth
  }
}

const role = ref<Role | null>(null)
const grants = ref<Grant[]>([])
const allPermissions = ref<Permission[]>([])
const loading = ref(true)
const loadError = ref('')
const granting = ref(false)

const newGrant = reactive({ permission_id: '', scope_type: 'GLOBAL', scope_id: '' })
const needsScopeId = computed(() => !['GLOBAL', 'SELF'].includes(newGrant.scope_type))
const canGrant = computed(() => !!newGrant.permission_id && (!needsScopeId.value || !!newGrant.scope_id))

function scopeLabel(scope: string) {
  const labels: Record<string, string> = { GLOBAL: 'سراسری', ORGANIZATION: 'سازمان', DEPARTMENT: 'دپارتمان', TEAM: 'تیم', SELF: 'خود کاربر' }
  return labels[scope] || scope
}

function permissionKey(id: number) {
  return allPermissions.value.find(p => p.id === id)?.key || `#${id}`
}

async function loadAll() {
  loading.value = true
  loadError.value = ''
  try {
    const [fetchedRole, grantList, permissions] = await Promise.all([
      apiFetch<Role>(`/core/roles/${roleId}`),
      apiFetch<Grant[]>(`/core/roles/${roleId}/permissions`),
      apiFetchPage<Permission>('/core/permissions', { per_page: 100 }).catch(() => ({ items: [] as Permission[] })),
    ])
    role.value = fetchedRole
    grants.value = grantList
    allPermissions.value = permissions.items
  }
  catch (err) {
    loadError.value = err instanceof ApiError ? err.message : 'بارگذاری نقش ناموفق بود.'
  }
  finally {
    loading.value = false
  }
  if (role.value) await matrix.load().catch(() => {})
}

async function addGrant() {
  granting.value = true
  try {
    const created = await apiFetch<Grant>(`/core/roles/${roleId}/permissions`, {
      method: 'POST',
      body: {
        permission_id: Number(newGrant.permission_id),
        scope_type: newGrant.scope_type,
        scope_id: needsScopeId.value ? Number(newGrant.scope_id) : null,
      },
    })
    grants.value.push(created)
    await matrix.load().catch(() => {})
    newGrant.permission_id = ''
    newGrant.scope_id = ''
    notify.success('مجوز اعطا شد')
  }
  catch (err) {
    notify.error(err instanceof ApiError ? err.message : 'اعطای مجوز ناموفق بود')
  }
  finally {
    granting.value = false
  }
}

async function revoke(grant: Grant) {
  try {
    await apiFetch(`/core/roles/${roleId}/permissions/${grant.id}`, { method: 'DELETE' })
    grants.value = grants.value.filter(g => g.id !== grant.id)
    await matrix.load().catch(() => {})
    notify.success('مجوز لغو شد')
  }
  catch (err) {
    notify.error(err instanceof ApiError ? err.message : 'لغو مجوز ناموفق بود')
  }
}

onMounted(loadAll)
usePageSeoMeta({ title: () => role.value?.display_name || 'نقش' })
</script>
