<template>
  <ContainerWrapper class="space-y-6 py-6 md:py-8">
    <AccessPageHeader
      section="مدیریت فروش و مشتریان"
      title="تنظیمات فروش"
      description="روش‌های پرداخت فروش. مشتریان، گریدها، استان‌ها و صنعت‌ها از بانک مشتریان می‌آیند و اینجا تعریف نمی‌شوند."
    />

    <Alert>
      <Icon name="lucide:info" class="size-4" />
      <AlertTitle>گریدها از بانک مشتریان می‌آیند</AlertTitle>
      <AlertDescription>
        فهرست گریدهای فروش همان فهرست «نام گرید» در پرونده مشتریان است و جداگانه ثبت نمی‌شود.
        برای افزودن، ویرایش یا حذف گرید، از بخش
        <NuxtLink to="/crm/customers" class="font-medium underline underline-offset-4">بانک مشتریان</NuxtLink>
        استفاده کنید.
      </AlertDescription>
    </Alert>

    <Card class="gap-4 p-5 shadow-none">
      <div class="flex items-center justify-between">
        <h2 class="font-semibold">روش‌های پرداخت</h2>
        <Button v-if="access.canCreateCatalog.value" size="sm" class="gap-2" @click="openMethod(null)">
          <Icon name="lucide:plus" class="size-4" /> روش جدید
        </Button>
      </div>
      <div class="overflow-x-auto">
        <Table v-if="store.paymentMethods.length">
          <TableHeader>
            <TableRow>
              <TableHead>نام</TableHead>
              <TableHead>تعداد فروش</TableHead>
              <TableHead class="text-right">عملیات</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            <TableRow v-for="m in store.paymentMethods" :key="m.id" :class="m.is_active ? '' : 'opacity-50'">
              <TableCell dir="auto">{{ m.name }}</TableCell>
              <TableCell class="text-muted-foreground">{{ faNum(m.sales_count) }}</TableCell>
              <TableCell class="text-right">
                <div class="flex justify-end gap-1">
                  <Button v-if="access.canUpdateCatalog.value" variant="ghost" size="icon" title="ویرایش" aria-label="ویرایش" @click="openMethod(m)">
                    <Icon name="lucide:pencil" class="size-4" />
                  </Button>
                  <Button v-if="access.canDeleteCatalog.value" variant="ghost" size="icon" class="text-destructive" title="حذف" aria-label="حذف" @click="removeMethod(m)">
                    <Icon name="lucide:trash-2" class="size-4" />
                  </Button>
                </div>
              </TableCell>
            </TableRow>
          </TableBody>
        </Table>
        <p v-else class="py-6 text-center text-sm text-muted-foreground">روشی ثبت نشده است.</p>
      </div>
    </Card>

    <Dialog v-model:open="methodOpen">
      <DialogContent class="sm:max-w-md">
        <DialogHeader class="text-right">
          <DialogTitle>{{ editingMethod ? 'ویرایش روش پرداخت' : 'روش پرداخت جدید' }}</DialogTitle>
          <DialogDescription>نام روش پرداخت (یکتا).</DialogDescription>
        </DialogHeader>
        <div class="space-y-3">
          <div class="space-y-1.5"><Label>نام</Label><Input v-model="methodName" dir="rtl" @keydown.enter="saveMethod" /></div>
          <p v-if="formError" class="text-sm text-destructive" role="alert">{{ formError }}</p>
        </div>
        <DialogFooter class="gap-2">
          <Button variant="outline" @click="methodOpen = false">انصراف</Button>
          <Button :disabled="saving" @click="saveMethod">ذخیره</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  </ContainerWrapper>
</template>

<script setup lang="ts">
import { ApiError } from '~/services/backendApi'
import { faNum } from '~/utils/crm'
import type { CrmPaymentMethod } from '~/stores/crm'

definePageMeta({ title: 'تنظیمات فروش' })

const store = useCrmStore()
const access = useCrmAccess()
const notify = useNotify()
const { confirm } = useConfirm()

const saving = ref(false)
const formError = ref('')
const msg = (e: unknown, fb: string) => (e instanceof ApiError ? e.message : fb)

const methodOpen = ref(false)
const editingMethod = ref<CrmPaymentMethod | null>(null)
const methodName = ref('')
function openMethod(m: CrmPaymentMethod | null) {
  editingMethod.value = m
  methodName.value = m?.name ?? ''
  formError.value = ''
  methodOpen.value = true
}
async function saveMethod() {
  if (!methodName.value.trim()) { formError.value = 'نام الزامی است.'; return }
  saving.value = true
  try {
    await store.savePaymentMethod({ name: methodName.value }, editingMethod.value?.id)
    methodOpen.value = false
    notify.success('روش پرداخت ذخیره شد')
    await store.loadCatalog(true)
  }
  catch (e) { formError.value = msg(e, 'ذخیره انجام نشد.') }
  finally { saving.value = false }
}

async function removeMethod(m: CrmPaymentMethod) {
  const used = m.sales_count > 0
  const ok = await confirm({
    title: 'حذف روش پرداخت',
    description: used
      ? `«${m.name}» در ${faNum(m.sales_count)} سند فروش استفاده شده است. با حذف آن، این اسناد بدون روش پرداخت (نامشخص) باقی می‌مانند و هیچ اطلاعات دیگری از آن‌ها پاک نمی‌شود. ادامه می‌دهید؟`
      : `«${m.name}» حذف شود؟`,
    confirmLabel: 'حذف', tone: 'danger',
  })
  if (!ok) return
  try {
    await store.removePaymentMethod(m.id, used)
    notify.success('روش پرداخت حذف شد')
  }
  catch (e) {
    // The list may have been stale (a sale was added meanwhile): the server then refuses with 409 --
    // reload so the next attempt shows the real count and asks for the explicit confirmation.
    notify.error('حذف انجام نشد', e instanceof ApiError && e.status === 409 ? 'این روش پرداخت هم‌اکنون در اسناد فروش استفاده می‌شود؛ دوباره تلاش کنید.' : msg(e, ''))
  }
  await store.loadCatalog(true)
}

onMounted(() => store.loadCatalog(true))
</script>
