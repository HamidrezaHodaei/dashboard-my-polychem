<template>
  <ContainerWrapper
    class="space-y-6 py-6 md:py-8"
    dir="rtl"
  >
    <AccessPageHeader
      title="مجوزها"
      description="فهرست ثابت کلیدهای مجوزی که به نقش‌ها واگذار می‌شوند"
      action-label="افزودن مجوز"
      @action="openCreate"
    />
    <Tabs
      v-model="tab"
      class="space-y-6"
    >
      <TabsList>
        <TabsTrigger value="catalog">
          فهرست مجوزها
        </TabsTrigger>
        <TabsTrigger value="tasks">
          وظایف
        </TabsTrigger>
      </TabsList>

      <TabsContent
        value="catalog"
        class="space-y-6"
      >
        <div class="grid gap-4 sm:grid-cols-3">
          <AccessStat
            label="مجوزها"
            :value="total"
            icon="lucide:key"
          />
          <AccessStat
            label="قابل واگذاری"
            :value="delegableCount"
            icon="lucide:share-2"
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
            در حال بارگذاری مجوزها…
          </div>
          <div
            v-else-if="loadError"
            class="p-8 text-center text-sm text-destructive"
          >
            {{ loadError }}
          </div>
          <Table v-else-if="permissions.length">
            <TableHeader>
              <TableRow>
                <TableHead>کلید</TableHead><TableHead>بخش</TableHead><TableHead>منبع</TableHead><TableHead>عمل</TableHead><TableHead>قابل واگذاری</TableHead><TableHead class="text-right">
                  عملیات
                </TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              <TableRow
                v-for="p in permissions"
                :key="p.id"
              >
                <TableCell class="font-mono text-sm">
                  {{ p.key }}
                </TableCell>
                <TableCell>{{ p.module }}</TableCell>
                <TableCell>{{ p.resource }}</TableCell>
                <TableCell>{{ p.action }}</TableCell>
                <TableCell>
                  <Badge variant="outline">
                    {{ p.is_delegable ? 'بله' : 'خیر' }}
                  </Badge>
                </TableCell>
                <TableCell class="text-right">
                  <div class="flex justify-end gap-1">
                    <Button
                      variant="ghost"
                      size="icon"
                      title="ویرایش"
                      @click="openEdit(p)"
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
                      @click="remove(p)"
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
            <span>نمایش {{ permissions.length }} مورد از {{ total }} مجوز</span>
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
      </TabsContent>

      <TabsContent value="tasks">
        <AccessTaskAssignmentRules />
      </TabsContent>
    </Tabs>

    <Dialog v-model:open="showForm">
      <DialogContent>
        <DialogHeader><DialogTitle>{{ editing ? 'ویرایش مجوز' : 'افزودن مجوز' }}</DialogTitle><DialogDescription>الگوی کلید: module.resource.action</DialogDescription></DialogHeader>
        <div class="space-y-4">
          <div
            v-if="!editing"
            class="space-y-1.5"
          >
            <Label>کلید</Label><Input
              v-model="form.key"
              placeholder="برای نمونه: tasks.task.read"
            />
          </div>
          <div class="space-y-1.5">
            <Label>توضیحات</Label><Input
              v-model="form.description"
              placeholder="توضیحات اختیاری"
            />
          </div>
          <div class="flex items-center gap-2">
            <Switch v-model="form.is_delegable" /><Label>قابل واگذاری</Label>
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

interface Permission { id: number, key: string, module: string, resource: string, action: string, is_delegable: boolean, description: string | null }

const tab = ref('catalog')
const page = ref(1)
const perPage = 20
const total = ref(0)
const permissions = ref<Permission[]>([])
const loading = ref(false)
const loadError = ref('')
const saving = ref(false)

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / perPage)))
const delegableCount = computed(() => permissions.value.filter(p => p.is_delegable).length)

async function load() {
  loading.value = true
  loadError.value = ''
  try {
    const result = await apiFetchPage<Permission>('/core/permissions', { page: page.value, per_page: perPage })
    permissions.value = result.items
    total.value = result.total
  }
  catch (err) {
    loadError.value = err instanceof ApiError ? err.message : 'Failed to load permissions.'
  }
  finally {
    loading.value = false
  }
}

const showForm = ref(false)
const editing = ref<Permission | null>(null)
const form = reactive({ key: '', description: '', is_delegable: false })

function openCreate() {
  editing.value = null
  form.key = ''
  form.description = ''
  form.is_delegable = false
  showForm.value = true
}
function openEdit(p: Permission) {
  editing.value = p
  form.description = p.description || ''
  form.is_delegable = p.is_delegable
  showForm.value = true
}

async function save() {
  saving.value = true
  try {
    if (editing.value) {
      await apiFetch(`/core/permissions/${editing.value.id}`, {
        method: 'PATCH',
        body: { description: form.description || null, is_delegable: form.is_delegable },
      })
      notify.success('مجوز به‌روزرسانی شد')
    }
    else {
      await apiFetch('/core/permissions', {
        method: 'POST',
        body: { key: form.key, description: form.description || null, is_delegable: form.is_delegable },
      })
      notify.success('مجوز ایجاد شد')
    }
    showForm.value = false
    await load()
  }
  catch (err) {
    notify.error(err instanceof ApiError ? err.message : 'ذخیرهٔ مجوز ناموفق بود')
  }
  finally {
    saving.value = false
  }
}

async function remove(p: Permission) {
  try {
    await apiFetch(`/core/permissions/${p.id}`, { method: 'DELETE' })
    notify.success('مجوز حذف شد')
    await load()
  }
  catch (err) {
    notify.error(err instanceof ApiError ? err.message : 'حذف مجوز ناموفق بود')
  }
}

onMounted(load)
usePageSeoMeta({ title: 'مجوزها' })
</script>
