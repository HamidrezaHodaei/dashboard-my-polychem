<template>
  <ContainerWrapper class="space-y-6 py-6 md:py-8">
    <AccessPageHeader
      title="مدیریت کالاهای خرید"
      description="فهرست کالاهایی که کارشناسان هنگام ثبت درخواست خرید از میان آن‌ها انتخاب می‌کنند. این فهرست مستقل از کالاهای سایر بخش‌هاست."
      section="تدارکات و لجستیک"
      action-label="تعریف کالای جدید"
      @action="openForm()"
    />

    <p v-if="!allowed" class="rounded-lg border border-destructive/40 bg-destructive/5 p-4 text-sm text-destructive">مدیریت کالاها فقط برای مدیر سامانه مجاز است.</p>

    <Card v-else class="overflow-hidden py-0 shadow-none">
      <div class="flex flex-wrap items-center gap-3 border-b p-4">
        <Input v-model="q" class="max-w-xs" placeholder="جستجوی نام یا کد کالا…" @input="debounced" />
        <select v-model="categoryId" class="h-9 rounded-md border border-input bg-transparent px-3 text-sm" @change="reload(1)">
          <option value="">همه گروه‌ها</option>
          <option v-for="c in store.meta?.categories" :key="c.id" :value="String(c.id)">{{ c.name }}</option>
        </select>
        <NuxtLink to="/procurement/purchases" class="mr-auto text-sm text-primary hover:underline">بازگشت به گزارشات خرید</NuxtLink>
      </div>
      <p v-if="error" class="p-4 text-sm text-destructive">{{ error }}</p>
      <div class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead class="bg-muted/50 text-muted-foreground"><tr>
            <th class="p-3 text-right">نام کالا</th><th class="p-3 text-right">کد کالا</th><th class="p-3 text-right">گروه کالایی</th><th class="p-3">وضعیت</th><th class="p-3">تعداد استفاده</th><th class="p-3" />
          </tr></thead>
          <tbody>
            <tr v-for="p in rows" :key="p.id" class="border-t">
              <td class="p-3">{{ p.name }}</td>
              <td class="p-3" dir="ltr"><span class="block text-right">{{ p.code || '—' }}</span></td>
              <td class="p-3">{{ p.category_name || '—' }}</td>
              <td class="p-3 text-center"><span class="rounded-full px-2 py-0.5 text-xs" :class="p.is_active ? 'bg-emerald-100 text-emerald-800' : 'bg-muted text-muted-foreground'">{{ p.is_active ? 'فعال' : 'غیرفعال' }}</span></td>
              <td class="p-3 text-center">{{ count(p.used_count ?? 0) }}</td>
              <td class="whitespace-nowrap p-3 text-left">
                <Button variant="ghost" size="sm" @click="openForm(p)">ویرایش</Button>
                <Button variant="ghost" size="sm" class="text-destructive" @click="remove(p)">حذف</Button>
              </td>
            </tr>
            <tr v-if="!rows.length && !loading"><td colspan="6" class="p-8 text-center text-muted-foreground">هنوز کالایی تعریف نشده است.</td></tr>
          </tbody>
        </table>
      </div>
      <div class="flex items-center justify-between border-t p-3 text-sm">
        <span class="text-muted-foreground">{{ count(total) }} کالا</span>
        <div class="flex items-center gap-2">
          <Button variant="outline" size="sm" :disabled="page <= 1" @click="reload(page - 1)">قبلی</Button>
          <span>{{ count(page) }} / {{ count(pages) }}</span>
          <Button variant="outline" size="sm" :disabled="page >= pages" @click="reload(page + 1)">بعدی</Button>
        </div>
      </div>
    </Card>

    <Dialog v-model:open="formOpen">
      <DialogContent dir="rtl">
        <DialogHeader><DialogTitle>{{ editing ? 'ویرایش کالا' : 'تعریف کالای جدید' }}</DialogTitle></DialogHeader>
        <div class="space-y-4">
          <PurchasesField label="نام کالا" required :error="errs.name"><Input v-model="form.name" /></PurchasesField>
          <PurchasesField label="کد کالا" :error="errs.code" hint="دستی وارد می‌شود؛ می‌تواند ترکیبی از حروف، عدد و - _ . / \ + # باشد (مثلاً RS-0012/A یا 007)">
            <Input v-model="form.code" dir="ltr" class="text-right" autocomplete="off" />
          </PurchasesField>
          <PurchasesField label="گروه کالایی (پیش‌فرض این کالا)" :error="errs.category_id">
            <select v-model="form.category_id" class="h-9 w-full rounded-md border border-input bg-transparent px-3 text-sm">
              <option value="">بدون گروه</option>
              <option v-for="c in store.meta?.categories" :key="c.id" :value="String(c.id)">{{ c.name }}</option>
            </select>
          </PurchasesField>
          <label class="flex items-center gap-2 text-sm"><input v-model="form.is_active" type="checkbox">فعال (قابل انتخاب در درخواست‌های جدید)</label>
          <p v-if="formError" class="text-sm text-destructive">{{ formError }}</p>
        </div>
        <DialogFooter><Button variant="outline" @click="formOpen = false">انصراف</Button><Button :disabled="busy" @click="submit">ذخیره</Button></DialogFooter>
      </DialogContent>
    </Dialog>
  </ContainerWrapper>
</template>

<script setup lang="ts">
import { ApiError } from '~/services/backendApi'
import { count, fieldErrors } from '~/utils/purchase'
import type { CatalogProduct } from '~/utils/purchase'

definePageMeta({ title: 'مدیریت کالاهای خرید' })

const store = usePurchasesStore()
const notify = useNotify()
const confirm = useConfirm()
const allowed = computed(() => store.can('manage_catalog'))
const rows = ref<CatalogProduct[]>([])
const total = ref(0)
const page = ref(1)
const perPage = 20
const q = ref('')
const categoryId = ref('')
const loading = ref(false)
const error = ref('')
const pages = computed(() => Math.max(1, Math.ceil(total.value / perPage)))

async function reload(p = page.value) {
  page.value = p
  loading.value = true
  error.value = ''
  try {
    const res = await store.listProducts({ q: q.value.trim() || undefined, category_id: categoryId.value || undefined, page: p, per_page: perPage })
    rows.value = res.items
    total.value = res.total
  }
  catch (e) { error.value = e instanceof ApiError ? e.message : 'بارگذاری انجام نشد.' }
  finally { loading.value = false }
}
let timer: ReturnType<typeof setTimeout> | undefined
const debounced = () => { clearTimeout(timer); timer = setTimeout(() => reload(1), 350) }

const formOpen = ref(false)
const editing = ref<CatalogProduct | null>(null)
const form = reactive({ name: '', code: '', category_id: '', is_active: true })
const errs = ref<Record<string, string>>({})
const formError = ref('')
const busy = ref(false)
function openForm(p?: CatalogProduct) {
  editing.value = p ?? null
  Object.assign(form, { name: p?.name ?? '', code: p?.code ?? '', category_id: p?.category_id ? String(p.category_id) : '', is_active: p?.is_active ?? true })
  errs.value = {}
  formError.value = ''
  formOpen.value = true
}
async function submit() {
  busy.value = true
  errs.value = {}
  formError.value = ''
  try {
    // the code is sent exactly as typed (a string, never converted to a number)
    await store.saveProduct({ name: form.name, code: form.code, category_id: form.category_id ? Number(form.category_id) : null, is_active: form.is_active }, editing.value?.id)
    formOpen.value = false
    notify.success(editing.value ? 'کالا ویرایش شد' : 'کالا تعریف شد')
    store.meta = null
    await Promise.all([reload(), store.loadMeta()])
  }
  catch (e) {
    errs.value = e instanceof ApiError ? fieldErrors(e.details) : {}
    formError.value = e instanceof ApiError ? e.message : 'ذخیره انجام نشد.'
  }
  finally { busy.value = false }
}
async function remove(p: CatalogProduct) {
  if (!(await confirm.confirm({ title: `حذف «${p.name}»؟`, description: 'کالایی که در درخواستی استفاده شده را نمی‌توان حذف کرد؛ آن را غیرفعال کنید.', confirmLabel: 'حذف', tone: 'danger' }))) return
  try { await store.deleteProduct(p.id); notify.success('کالا حذف شد'); await reload() }
  catch (e) { notify.error('حذف انجام نشد', e instanceof ApiError ? e.message : undefined) }
}

onMounted(async () => {
  await store.loadMeta().catch(() => {})
  if (allowed.value) await reload(1)
})
</script>
