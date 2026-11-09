<template>
  <ContainerWrapper
    class="space-y-6 py-6 md:py-8"
    dir="rtl"
  >
    <AccessPageHeader
      title="تیم‌ها"
      description="تیم‌های زیرمجموعهٔ هر دپارتمان"
      action-label="افزودن تیم"
      @action="openCreate"
    />
    <div class="grid gap-4 sm:grid-cols-3">
      <AccessStat
        label="تیم‌ها"
        :value="total"
        icon="lucide:network"
      />
      <AccessStat
        label="فعال"
        :value="activeCount"
        icon="lucide:check-circle"
      />
      <AccessStat
        label="صفحه"
        :value="`${page} / ${totalPages}`"
        icon="lucide:layout-list"
      />
    </div>

    <Card class="overflow-hidden py-0 shadow-none">
      <div
        v-if="loading"
        class="p-8 text-center text-sm text-muted-foreground"
      >
        در حال بارگذاری تیم‌ها…
      </div>
      <div
        v-else-if="loadError"
        class="p-8 text-center text-sm text-destructive"
      >
        {{ loadError }}
      </div>
      <Table v-else-if="teams.length">
        <TableHeader>
          <TableRow>
            <TableHead>تیم</TableHead><TableHead>دپارتمان</TableHead><TableHead>وضعیت</TableHead><TableHead class="text-right">
              عملیات
            </TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          <TableRow
            v-for="team in teams"
            :key="team.id"
          >
            <TableCell class="font-medium">
              {{ team.name }}
            </TableCell>
            <TableCell class="text-muted-foreground">
              {{ deptName(team.department_id) }}
            </TableCell>
            <TableCell><AccessStatusBadge :status="team.is_active ? 'active' : 'inactive'" /></TableCell>
            <TableCell class="text-right">
              <div class="flex justify-end gap-1">
                <Button
                  variant="ghost"
                  size="icon"
                  title="اعضا"
                  @click="openMembers(team)"
                >
                  <Icon
                    name="lucide:users"
                    class="size-4"
                  />
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  title="ویرایش"
                  @click="openEdit(team)"
                >
                  <Icon
                    name="lucide:pencil"
                    class="size-4"
                  />
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  title="حذف"
                  class="text-destructive"
                  @click="remove(team)"
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
      <div class="flex items-center justify-between border-t p-4 text-sm text-muted-foreground">
        <span>نمایش {{ teams.length }} مورد از {{ total }} تیم</span>
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

    <Dialog v-model:open="showForm">
      <DialogContent>
        <DialogHeader><DialogTitle>{{ editing ? 'ویرایش تیم' : 'افزودن تیم' }}</DialogTitle><DialogDescription>اطلاعات تیم.</DialogDescription></DialogHeader>
        <div class="space-y-4">
          <div class="space-y-1.5">
            <Label>نام</Label><Input
              v-model="form.name"
              placeholder="نام تیم"
            />
          </div>
          <div class="space-y-1.5">
            <Label>دپارتمان</Label>
            <Select
              v-model="form.department_id"
              :disabled="!!editing"
            >
              <SelectTrigger class="w-full">
                <SelectValue placeholder="انتخاب دپارتمان" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem
                  v-for="d in allDepartments"
                  :key="d.id"
                  :value="String(d.id)"
                >
                  {{ d.name }}
                </SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div
            v-if="editing"
            class="flex items-center gap-2"
          >
            <Switch v-model="form.is_active" /><Label>فعال</Label>
          </div>
        </div>
        <DialogFooter>
          <Button
            variant="outline"
            @click="showForm = false"
          >
            انصراف
          </Button><Button
            :disabled="saving || !form.department_id"
            @click="save"
          >
            ذخیره
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>

    <Dialog v-model:open="showMembers">
      <DialogContent class="max-w-lg">
        <DialogHeader><DialogTitle>اعضای تیم: {{ membersFor?.name }}</DialogTitle><DialogDescription>مدیریت عضویت در تیم.</DialogDescription></DialogHeader>
        <div class="flex gap-2">
          <Select v-model="userToAdd">
            <SelectTrigger class="w-full">
              <SelectValue placeholder="انتخاب کاربر برای افزودن" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem
                v-for="u in addableUsers"
                :key="u.id"
                :value="String(u.id)"
              >
                {{ u.full_name }} ({{ u.username }})
              </SelectItem>
            </SelectContent>
          </Select>
          <Button
            :disabled="!userToAdd || memberSaving"
            @click="addMember"
          >
            افزودن
          </Button>
        </div>
        <div class="max-h-72 space-y-1 overflow-y-auto">
          <div
            v-if="!members.length"
            class="py-6 text-center text-sm text-muted-foreground"
          >
            هنوز عضوی ثبت نشده است.
          </div>
          <div
            v-for="m in members"
            :key="m.id"
            class="flex items-center justify-between rounded-md border p-2.5"
          >
            <span class="text-sm font-medium">{{ userName(m.user_id) }}</span>
            <Button
              variant="ghost"
              size="icon"
              class="text-destructive"
              @click="removeMember(m)"
            >
              <Icon
                name="lucide:trash-2"
                class="size-4"
              />
            </Button>
          </div>
        </div>
        <DialogFooter>
          <Button
            variant="outline"
            @click="showMembers = false"
          >
            بستن
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  </ContainerWrapper>
</template>

<script setup lang="ts">
const notify = useNotify()
import { ApiError, apiFetch, apiFetchPage } from '~/services/backendApi'
import type { BackendUser } from '~/stores/auth'

interface Team { id: number, name: string, department_id: number, manager_user_id: number | null, is_active: boolean }
interface Department { id: number, name: string, organization_id: number }
interface TeamMember { id: number, team_id: number, user_id: number }

const page = ref(1)
const perPage = 20
const total = ref(0)
const teams = ref<Team[]>([])
const allDepartments = ref<Department[]>([])
const allUsers = ref<BackendUser[]>([])
const loading = ref(false)
const loadError = ref('')
const saving = ref(false)

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / perPage)))
const activeCount = computed(() => teams.value.filter(t => t.is_active).length)
function deptName(id: number) {
  return allDepartments.value.find(d => d.id === id)?.name || `#${id}`
}
function userName(id: number) {
  return allUsers.value.find(u => u.id === id)?.full_name || `#${id}`
}

async function load() {
  loading.value = true
  loadError.value = ''
  try {
    const [result, depts, users] = await Promise.all([
      apiFetchPage<Team>('/core/teams', { page: page.value, per_page: perPage }),
      allDepartments.value.length ? Promise.resolve({ items: allDepartments.value }) : apiFetchPage<Department>('/core/departments', { per_page: 200 }),
      allUsers.value.length ? Promise.resolve({ items: allUsers.value }) : apiFetchPage<BackendUser>('/core/users', { per_page: 200 }),
    ])
    teams.value = result.items
    total.value = result.total
    allDepartments.value = depts.items
    allUsers.value = users.items
  }
  catch (err) {
    loadError.value = err instanceof ApiError ? err.message : 'بارگذاری تیم‌ها ناموفق بود.'
  }
  finally {
    loading.value = false
  }
}

const showForm = ref(false)
const editing = ref<Team | null>(null)
const form = reactive({ name: '', department_id: '', is_active: true })

function openCreate() {
  editing.value = null
  form.name = ''
  form.department_id = ''
  form.is_active = true
  showForm.value = true
}
function openEdit(team: Team) {
  editing.value = team
  form.name = team.name
  form.department_id = String(team.department_id)
  form.is_active = team.is_active
  showForm.value = true
}

async function save() {
  saving.value = true
  try {
    if (editing.value) {
      await apiFetch(`/core/teams/${editing.value.id}`, {
        method: 'PATCH',
        body: { name: form.name, is_active: form.is_active },
      })
      notify.success('تیم به‌روزرسانی شد')
    }
    else {
      await apiFetch('/core/teams', {
        method: 'POST',
        body: { name: form.name, department_id: Number(form.department_id) },
      })
      notify.success('تیم ایجاد شد')
    }
    showForm.value = false
    await load()
  }
  catch (err) {
    notify.error(err instanceof ApiError ? err.message : 'ذخیرهٔ تیم ناموفق بود')
  }
  finally {
    saving.value = false
  }
}

async function remove(team: Team) {
  try {
    await apiFetch(`/core/teams/${team.id}`, { method: 'DELETE' })
    notify.success('تیم حذف شد')
    await load()
  }
  catch (err) {
    notify.error(err instanceof ApiError ? err.message : 'حذف تیم ناموفق بود')
  }
}

// --- Members ---
const showMembers = ref(false)
const membersFor = ref<Team | null>(null)
const members = ref<TeamMember[]>([])
const userToAdd = ref('')
const memberSaving = ref(false)
const addableUsers = computed(() => allUsers.value.filter(u => !members.value.some(m => m.user_id === u.id)))

async function openMembers(team: Team) {
  membersFor.value = team
  userToAdd.value = ''
  showMembers.value = true
  try {
    members.value = await apiFetch<TeamMember[]>(`/core/teams/${team.id}/members`)
  }
  catch (err) {
    notify.error(err instanceof ApiError ? err.message : 'بارگذاری اعضا ناموفق بود')
  }
}

async function addMember() {
  if (!membersFor.value || !userToAdd.value) return
  memberSaving.value = true
  try {
    const created = await apiFetch<TeamMember>(`/core/teams/${membersFor.value.id}/members`, {
      method: 'POST',
      body: { user_id: Number(userToAdd.value) },
    })
    members.value.push(created)
    userToAdd.value = ''
    notify.success('عضو افزوده شد')
  }
  catch (err) {
    notify.error(err instanceof ApiError ? err.message : 'افزودن عضو ناموفق بود')
  }
  finally {
    memberSaving.value = false
  }
}

async function removeMember(member: TeamMember) {
  if (!membersFor.value) return
  try {
    await apiFetch(`/core/teams/${membersFor.value.id}/members/${member.user_id}`, { method: 'DELETE' })
    members.value = members.value.filter(m => m.id !== member.id)
    notify.success('عضو حذف شد')
  }
  catch (err) {
    notify.error(err instanceof ApiError ? err.message : 'حذف عضو ناموفق بود')
  }
}

onMounted(load)
usePageSeoMeta({ title: 'تیم‌ها' })
</script>
