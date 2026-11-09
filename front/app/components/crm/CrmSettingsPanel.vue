<template>
  <section class="crm-settings-panel space-y-6">
    <div>
      <h2 class="text-xl font-semibold">
        تنظیمات
      </h2><p class="mt-1 text-sm text-muted-foreground">
        ?????? ???????? ????? ??????? ?? ?? ??????? ???? ? ???????? ??????? ???????.
      </p>
    </div>
    <Card class="overflow-hidden py-0 shadow-none">
      <div class="flex gap-1 overflow-x-auto border-b px-4">
        <button
          v-for="section in sections"
          :key="section.key"
          class="crm-settings-tab"
          :class="activeSection === section.key && 'crm-settings-tab-active'"
          @click="activeSection = section.key"
        >
          <Icon
            :name="section.icon"
            class="size-4"
          />{{ section.label }}
        </button>
      </div><div class="p-5">
        <div class="mb-4 flex flex-wrap items-center justify-between gap-3">
          <div>
            <h3 class="font-semibold">
              {{ currentSection.label }}
            </h3><p class="mt-1 text-sm text-muted-foreground">
              {{ currentSection.description }}
            </p>
          </div><Button
            class="gap-2"
            @click="openCreate"
          >
            <Icon
              name="lucide:plus"
              class="size-4"
            /> افزودن {{ currentSection.singular }}
          </Button>
        </div><div class="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          <div
            v-for="item in currentItems"
            :key="item.id"
            class="flex items-center justify-between gap-3 rounded-lg border bg-muted/20 px-4 py-3"
          >
            <div class="min-w-0">
              <p class="truncate text-sm font-medium">
                {{ item.name }}
              </p><p
                v-if="item.code || item.category"
                class="mt-1 truncate text-xs text-muted-foreground"
              >
                {{ item.code || item.category }}
              </p>
            </div><div class="flex shrink-0 gap-1">
              <Button
                variant="ghost"
                size="icon"
                title="ویرایش"
                @click="openEdit(item)"
              >
                <Icon
                  name="lucide:pencil"
                  class="size-4"
                />
              </Button><Button
                variant="ghost"
                size="icon"
                title="حذف"
                class="hover:text-destructive"
                @click="remove(item)"
              >
                <Icon
                  name="lucide:trash-2"
                  class="size-4"
                />
              </Button>
            </div>
          </div>
        </div><AccessEmptyState v-if="!currentItems.length" />
      </div>
    </Card>
    <Card class="gap-4 p-5 shadow-none">
      <div class="flex items-center gap-3">
        <div class="flex size-10 items-center justify-center rounded-lg bg-primary/10 text-primary">
          <Icon
            name="lucide:database"
            class="size-5"
          />
        </div><div>
          <h3 class="font-semibold">
            اتصال به سرور
          </h3><p class="text-sm text-muted-foreground">
            نشانی فعلی API مدیریت ارتباط با مشتری
          </p>
        </div>
      </div><code class="block rounded-md bg-muted px-3 py-2 text-sm">{{ apiBase }}</code><label class="flex items-center justify-between border-t pt-4 text-sm"><span>نمایش فاکتورهای برگشتی در گزارش‌ها</span><Switch
        :model-value="showReturns"
        @update:model-value="$emit('update:showReturns', $event === true)"
      /></label>
    </Card>
    <Dialog v-model:open="dialogOpen">
      <DialogContent>
        <DialogHeader><DialogTitle>{{ editingItem ? `ویرایش ${currentSection.singular}` : `افزودن ${currentSection.singular}` }}</DialogTitle><DialogDescription>تغییرات از طریق API مدیریت ارتباط با مشتری ذخیره می‌شوند.</DialogDescription></DialogHeader><div class="space-y-4">
          <Input
            v-model="form.name"
            :placeholder="`??? ${currentSection.singular}`"
          /><Input
            v-if="activeSection === 'products'"
            v-model="form.code"
            placeholder="کد کالا"
          /><Input
            v-if="activeSection === 'products'"
            v-model="form.category"
            placeholder="دسته‌بندی"
          />
        </div><DialogFooter>
          <Button
            variant="outline"
            @click="dialogOpen = false"
          >
            انصراف
          </Button><Button
            :disabled="saving || !form.name.trim()"
            @click="save"
          >
            {{ saving ? 'در حال ذخیره...' : 'ذخیره' }}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  </section>
</template>

<script setup lang="ts">
const notify = useNotify()
import type { CrmLookup } from '~/composables/useCrmDashboard'

const props = defineProps<{ apiBase: string, products: CrmLookup[], provinces: CrmLookup[], industries: CrmLookup[], paymentMethods: CrmLookup[], showReturns: boolean }>()
const emit = defineEmits<{ 'update:showReturns': [value: boolean], 'refresh': [] }>()
const sections = [{ key: 'products', label: 'کالاها', singular: 'کالا', description: 'کالاهای ثبت‌شده در سوابق فروش.', icon: 'lucide:package' }, { key: 'provinces', label: 'استان‌ها', singular: 'استان', description: 'موقعیت جغرافیایی مشتریان.', icon: 'lucide:map-pin' }, { key: 'industries', label: 'صنایع', singular: 'صنعت', description: 'دسته‌بندی صنایع مشتریان.', icon: 'lucide:factory' }, { key: 'payments', label: 'روش‌های پرداخت', singular: 'روش پرداخت', description: 'روش‌های پرداخت فاکتورها.', icon: 'lucide:credit-card' }] as const
const activeSection = ref<(typeof sections)[number]['key']>('products')
const dialogOpen = ref(false)
const saving = ref(false)
const editingItem = ref<CrmLookup | null>(null)
const form = reactive({ name: '', code: '', category: '' })
const currentSection = computed(() => sections.find(section => section.key === activeSection.value) || sections[0])
const currentItems = computed(() => ({ products: props.products, provinces: props.provinces, industries: props.industries, payments: props.paymentMethods }[activeSection.value]))
const endpoint = computed(() => ({ products: 'products', provinces: 'provinces', industries: 'industries', payments: 'payment-methods' }[activeSection.value]))
function openCreate() { editingItem.value = null; Object.assign(form, { name: '', code: '', category: '' }); dialogOpen.value = true }
function openEdit(item: CrmLookup) { editingItem.value = item; Object.assign(form, { name: item.name, code: item.code || '', category: item.category || '' }); dialogOpen.value = true }
async function save() {
  saving.value = true; try { await $fetch(`${props.apiBase}/api/${endpoint.value}${editingItem.value ? `/${editingItem.value.id}` : ''}`, { method: editingItem.value ? 'PUT' : 'POST', body: form, credentials: 'include' }); notify.success(`${currentSection.value.singular} ????? ??`); dialogOpen.value = false; emit('refresh') }
  catch { notify.error(`?????? ${currentSection.value.singular} ?????? ???`) }
  finally { saving.value = false }
}
async function remove(item: CrmLookup) {
  if (!confirm(`آیا از حذف ${item.name} مطمئن هستید؟`)) return; try { await $fetch(`${props.apiBase}/api/${endpoint.value}/${item.id}`, { method: 'DELETE', credentials: 'include' }); notify.success(`${currentSection.value.singular} ??? ??`); emit('refresh') }
  catch { notify.error(`??? ${currentSection.value.singular} ?????? ???`) }
}
</script>

<style scoped>
.crm-settings-tab { display: inline-flex; align-items: center; gap: .5rem; white-space: nowrap; border-bottom: 2px solid transparent; padding: .8rem .75rem; font-size: .875rem; color: var(--muted-foreground); }
.crm-settings-tab-active { border-color: var(--primary); color: var(--primary); font-weight: 600; }
</style>
