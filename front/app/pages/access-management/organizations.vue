<template>
  <ContainerWrapper
    class="space-y-6 py-6 md:py-8"
    dir="rtl"
  >
    <AccessPageHeader
      title="سازمان"
      description="ساختار شرکت و واحدهای سازمانی"
      action-label="افزودن سازمان"
      @action="openCreate"
    />
    <div class="grid gap-4 sm:grid-cols-3">
      <AccessStat
        label="تعداد سازمان‌ها"
        :value="total"
        icon="lucide:building-2"
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
        در حال بارگذاری سازمان‌ها…
      </div>
      <div
        v-else-if="loadError"
        class="p-8 text-center text-sm text-destructive"
      >
        {{ loadError }}
      </div>
      <Table v-else-if="organizations.length">
        <TableHeader>
          <TableRow>
            <TableHead>سازمان</TableHead><TableHead>والد</TableHead><TableHead>وضعیت</TableHead><TableHead class="text-right">
              عملیات
            </TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          <TableRow
            v-for="org in organizations"
            :key="org.id"
          >
            <TableCell class="font-medium">
              <div class="flex items-center gap-3">
                <div class="flex size-9 items-center justify-center rounded-md bg-primary/10 text-primary">
                  <Icon
                    name="lucide:building-2"
                    class="size-4"
                  />
                </div>
                {{ org.name }}
              </div>
            </TableCell>
            <TableCell class="text-muted-foreground">
              {{ orgName(org.parent_organization_id) }}
            </TableCell>
            <TableCell><AccessStatusBadge :status="org.is_active ? 'active' : 'inactive'" /></TableCell>
            <TableCell class="text-right">
              <div class="flex justify-end gap-1">
                <Button
                  variant="ghost"
                  size="icon"
                  title="مدیریت دپارتمان‌ها"
                  @click="openDepartments(org)"
                >
                  <Icon
                    name="lucide:network"
                    class="size-4"
                  />
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  title="ویرایش"
                  @click="openEdit(org)"
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
                  @click="remove(org)"
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
        <span>نمایش {{ organizations.length }} مورد از {{ total }} سازمان</span>
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
        <DialogHeader><DialogTitle>{{ editing ? 'ویرایش سازمان' : 'افزودن سازمان' }}</DialogTitle><DialogDescription>اطلاعات سازمان.</DialogDescription></DialogHeader>
        <div class="space-y-4">
          <div class="space-y-1.5">
            <Label>نام</Label><Input
              v-model="form.name"
              placeholder="نام سازمان"
            />
          </div>
          <div class="space-y-1.5">
            <Label>سازمان والد</Label>
            <Select v-model="form.parent_organization_id">
              <SelectTrigger class="w-full">
                <SelectValue placeholder="بدون مورد" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="none">
                  بدون مورد
                </SelectItem>
                <SelectItem
                  v-for="o in organizations.filter(o => o.id !== editing?.id)"
                  :key="o.id"
                  :value="String(o.id)"
                >
                  {{ o.name }}
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
            :disabled="saving"
            @click="save"
          >
            ذخیره
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>

    <Dialog v-model:open="showDepartments">
      <DialogContent class="max-w-lg">
        <DialogHeader><DialogTitle>دپارتمان‌های {{ departmentsFor?.name }}</DialogTitle><DialogDescription>مدیریت دپارتمان‌های این سازمان.</DialogDescription></DialogHeader>
        <div class="flex gap-2">
          <Input
            v-model="newDeptName"
            placeholder="نام دپارتمان جدید"
          />
          <Button
            :disabled="!newDeptName || deptSaving"
            @click="addDepartment"
          >
            افزودن
          </Button>
        </div>
        <div class="max-h-72 space-y-1 overflow-y-auto">
          <div
            v-if="!departments.length"
            class="py-6 text-center text-sm text-muted-foreground"
          >
            هنوز دپارتمانی ثبت نشده است.
          </div>
          <div
            v-for="dept in departments"
            :key="dept.id"
            class="flex items-center justify-between rounded-md border p-2.5"
          >
            <span class="text-sm font-medium">{{ dept.name }}</span>
            <Button
              variant="ghost"
              size="icon"
              class="text-destructive"
              @click="removeDepartment(dept)"
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
            @click="showDepartments = false"
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

interface Organization { id: number, name: string, parent_organization_id: number | null, is_active: boolean }
interface Department { id: number, name: string, organization_id: number, is_active: boolean }

const page = ref(1)
const perPage = 20
const total = ref(0)
const organizations = ref<Organization[]>([])
const loading = ref(false)
const loadError = ref('')
const saving = ref(false)

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / perPage)))
const activeCount = computed(() => organizations.value.filter(o => o.is_active).length)
function orgName(id: number | null) {
  if (!id) return '—'
  return organizations.value.find(o => o.id === id)?.name || `#${id}`
}

async function load() {
  loading.value = true
  loadError.value = ''
  try {
    const result = await apiFetchPage<Organization>('/core/organizations', { page: page.value, per_page: perPage })
    organizations.value = result.items
    total.value = result.total
  }
  catch (err) {
    loadError.value = err instanceof ApiError ? err.message : 'بارگذاری سازمان‌ها ناموفق بود.'
  }
  finally {
    loading.value = false
  }
}

const showForm = ref(false)
const editing = ref<Organization | null>(null)
const form = reactive({ name: '', parent_organization_id: 'none' as string, is_active: true })

function openCreate() {
  editing.value = null
  form.name = ''
  form.parent_organization_id = 'none'
  form.is_active = true
  showForm.value = true
}
function openEdit(org: Organization) {
  editing.value = org
  form.name = org.name
  form.parent_organization_id = org.parent_organization_id ? String(org.parent_organization_id) : 'none'
  form.is_active = org.is_active
  showForm.value = true
}

async function save() {
  saving.value = true
  try {
    const parentId = form.parent_organization_id === 'none' ? null : Number(form.parent_organization_id)
    if (editing.value) {
      await apiFetch(`/core/organizations/${editing.value.id}`, {
        method: 'PATCH',
        body: { name: form.name, parent_organization_id: parentId, is_active: form.is_active },
      })
      notify.success('سازمان به‌روزرسانی شد')
    }
    else {
      await apiFetch('/core/organizations', {
        method: 'POST',
        body: { name: form.name, parent_organization_id: parentId },
      })
      notify.success('سازمان ایجاد شد')
    }
    showForm.value = false
    await load()
  }
  catch (err) {
    notify.error(err instanceof ApiError ? err.message : 'ذخیرهٔ سازمان ناموفق بود')
  }
  finally {
    saving.value = false
  }
}

async function remove(org: Organization) {
  try {
    await apiFetch(`/core/organizations/${org.id}`, { method: 'DELETE' })
    notify.success('سازمان حذف شد')
    await load()
  }
  catch (err) {
    notify.error(err instanceof ApiError ? err.message : 'حذف سازمان ناموفق بود')
  }
}

// --- دپارتمان (nested under an organization) ---
const showDepartments = ref(false)
const departmentsFor = ref<Organization | null>(null)
const departments = ref<Department[]>([])
const newDeptName = ref('')
const deptSaving = ref(false)

async function openDepartments(org: Organization) {
  departmentsFor.value = org
  newDeptName.value = ''
  showDepartments.value = true
  try {
    // The departments list endpoint has no organization_id filter, so
    // fetch a large page and filter client-side.
    const result = await apiFetchPage<Department>('/core/departments', { per_page: 200 })
    departments.value = result.items.filter(d => d.organization_id === org.id)
  }
  catch (err) {
    notify.error(err instanceof ApiError ? err.message : 'بارگذاری دپارتمان‌ها ناموفق بود')
  }
}

async function addDepartment() {
  if (!departmentsFor.value || !newDeptName.value) return
  deptSaving.value = true
  try {
    const created = await apiFetch<Department>('/core/departments', {
      method: 'POST',
      body: { name: newDeptName.value, organization_id: departmentsFor.value.id },
    })
    departments.value.push(created)
    newDeptName.value = ''
  }
  catch (err) {
    notify.error(err instanceof ApiError ? err.message : 'ایجاد دپارتمان ناموفق بود')
  }
  finally {
    deptSaving.value = false
  }
}

async function removeDepartment(dept: Department) {
  try {
    await apiFetch(`/core/departments/${dept.id}`, { method: 'DELETE' })
    departments.value = departments.value.filter(d => d.id !== dept.id)
  }
  catch (err) {
    notify.error(err instanceof ApiError ? err.message : 'حذف دپارتمان ناموفق بود')
  }
}

onMounted(load)
usePageSeoMeta({ title: 'سازمان‌ها' })
</script>
