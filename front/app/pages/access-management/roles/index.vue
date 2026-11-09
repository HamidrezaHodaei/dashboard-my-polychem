<template>
  <ContainerWrapper
    class="space-y-6 py-6 md:py-8"
    dir="rtl"
  >
    <AccessPageHeader
      title="نقش‌ها"
      description="نقش‌ها مجموعه‌ای از مجوزها را برای گروهی از کاربران فراهم می‌کنند"
      action-label="افزودن نقش"
      @action="openCreate"
    />
    <div class="grid gap-4 sm:grid-cols-3">
      <AccessStat
        label="نقش‌ها"
        :value="total"
        icon="lucide:shield"
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
        در حال بارگذاری نقش‌ها…
      </div>
      <div
        v-else-if="loadError"
        class="p-8 text-center text-sm text-destructive"
      >
        {{ loadError }}
      </div>
      <Table v-else-if="roles.length">
        <TableHeader>
          <TableRow>
            <TableHead>نقش</TableHead><TableHead>توضیحات</TableHead><TableHead>سیستمی</TableHead><TableHead>وضعیت</TableHead><TableHead class="text-right">
              عملیات
            </TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          <TableRow
            v-for="role in roles"
            :key="role.id"
          >
            <TableCell class="font-medium">
              <NuxtLink
                :to="`/access-management/roles/${role.id}`"
                class="hover:underline"
              >
                {{ role.display_name }}
              </NuxtLink><p class="text-xs text-muted-foreground">
                {{ role.name }}
              </p>
            </TableCell>
            <TableCell class="text-muted-foreground">
              {{ role.description || '—' }}
            </TableCell>
            <TableCell>
              <Badge
                v-if="role.is_system_role"
                variant="outline"
              >
                سیستمی
              </Badge><span v-else>—</span>
            </TableCell>
            <TableCell><AccessStatusBadge :status="role.is_active ? 'active' : 'inactive'" /></TableCell>
            <TableCell class="text-right">
              <div class="flex justify-end gap-1">
                <Button
                  variant="ghost"
                  size="icon"
                  title="مجوزها"
                  as-child
                >
                  <NuxtLink :to="`/access-management/roles/${role.id}`">
                    <Icon
                      name="lucide:key"
                      class="size-4"
                    />
                  </NuxtLink>
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  title="ویرایش"
                  @click="openEdit(role)"
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
                  :disabled="role.is_system_role"
                  @click="remove(role)"
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
        <span>نمایش {{ roles.length }} مورد از {{ total }} نقش</span>
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
        <DialogHeader><DialogTitle>{{ editing ? 'ویرایش نقش' : 'افزودن نقش' }}</DialogTitle><DialogDescription>اطلاعات نقش.</DialogDescription></DialogHeader>
        <div class="space-y-4">
          <div
            v-if="!editing"
            class="space-y-1.5"
          >
            <Label>نام (کلید داخلی)</Label><Input
              v-model="form.name"
              placeholder="برای نمونه: sales_manager"
            />
          </div>
          <div class="space-y-1.5">
            <Label>نام نمایشی</Label><Input
              v-model="form.display_name"
              placeholder="برای نمونه: مدیر فروش"
            />
          </div>
          <div class="space-y-1.5">
            <Label>توضیحات</Label><Input
              v-model="form.description"
              placeholder="توضیحات اختیاری"
            />
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
  </ContainerWrapper>
</template>

<script setup lang="ts">
const notify = useNotify()
import { ApiError, apiFetch, apiFetchPage } from '~/services/backendApi'

interface Role { id: number, name: string, display_name: string, description: string | null, is_system_role: boolean, is_active: boolean }

const page = ref(1)
const perPage = 20
const total = ref(0)
const roles = ref<Role[]>([])
const loading = ref(false)
const loadError = ref('')
const saving = ref(false)

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / perPage)))
const activeCount = computed(() => roles.value.filter(r => r.is_active).length)

async function load() {
  loading.value = true
  loadError.value = ''
  try {
    const result = await apiFetchPage<Role>('/core/roles', { page: page.value, per_page: perPage, include_inactive: true })
    roles.value = result.items
    total.value = result.total
  }
  catch (err) {
    loadError.value = err instanceof ApiError ? err.message : 'Failed to load roles.'
  }
  finally {
    loading.value = false
  }
}

const showForm = ref(false)
const editing = ref<Role | null>(null)
const form = reactive({ name: '', display_name: '', description: '', is_active: true })

function openCreate() {
  editing.value = null
  form.name = ''
  form.display_name = ''
  form.description = ''
  form.is_active = true
  showForm.value = true
}
function openEdit(role: Role) {
  editing.value = role
  form.display_name = role.display_name
  form.description = role.description || ''
  form.is_active = role.is_active
  showForm.value = true
}

async function save() {
  saving.value = true
  try {
    if (editing.value) {
      await apiFetch(`/core/roles/${editing.value.id}`, {
        method: 'PATCH',
        body: { display_name: form.display_name, description: form.description || null, is_active: form.is_active },
      })
      notify.success('نقش به‌روزرسانی شد')
    }
    else {
      await apiFetch('/core/roles', {
        method: 'POST',
        body: { name: form.name, display_name: form.display_name, description: form.description || null },
      })
      notify.success('نقش ایجاد شد')
    }
    showForm.value = false
    await load()
  }
  catch (err) {
    notify.error(err instanceof ApiError ? err.message : 'ذخیرهٔ نقش ناموفق بود')
  }
  finally {
    saving.value = false
  }
}

async function remove(role: Role) {
  try {
    await apiFetch(`/core/roles/${role.id}`, { method: 'DELETE' })
    notify.success('نقش حذف شد')
    await load()
  }
  catch (err) {
    notify.error(err instanceof ApiError ? err.message : 'حذف نقش ناموفق بود')
  }
}

onMounted(load)
usePageSeoMeta({ title: 'نقش‌ها' })
</script>
