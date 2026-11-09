<!-- /components/customer/OptionsDialog.vue  → <CustomerOptionsDialog />
     مدیریت فهرست «نام محصول» و «نام گرید» فرم مشتری: افزودن، تغییر نام، مخفی/نمایش، جابه‌جایی و حذف. -->
<template>
  <Dialog :open="open" @update:open="v => emit('update:open', v)">
    <DialogContent class="flex max-h-[85vh] flex-col gap-0 overflow-hidden p-0 sm:max-w-xl">
      <DialogHeader class="border-b px-6 py-4 text-right">
        <DialogTitle class="text-lg font-semibold">محصول و گرید</DialogTitle>
        <DialogDescription>
          این فهرست‌ها در فرم مشتری برای «نام محصول» و «گرید» نمایش داده می‌شوند.
        </DialogDescription>
      </DialogHeader>

      <div class="flex gap-2 border-b px-6 py-3" role="tablist" aria-label="نوع فهرست">
        <button
          v-for="t in tabs"
          :key="t.kind"
          type="button"
          role="tab"
          class="rounded-full border px-4 py-1.5 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          :class="kind === t.kind ? 'border-primary bg-primary text-primary-foreground' : 'border-border hover:bg-muted'"
          :aria-selected="kind === t.kind"
          @click="switchKind(t.kind)"
        >
          {{ t.label }} <span class="opacity-70">({{ countOf(t.kind) }})</span>
        </button>
      </div>

      <form class="flex gap-2 border-b px-6 py-4" @submit.prevent="add">
        <Input
          v-model="newName"
          dir="auto"
          :placeholder="kind === 'GRADE' ? 'نام گرید جدید' : 'نام محصول جدید'"
          maxlength="255"
          :disabled="busy"
        />
        <Button type="submit" class="gap-1.5" :disabled="busy || !newName.trim()">
          <Icon name="lucide:plus" class="size-4" /> افزودن
        </Button>
      </form>

      <div class="flex-1 overflow-y-auto px-3 py-2">
        <p v-if="!items.length" class="p-6 text-center text-sm text-muted-foreground">
          هنوز موردی در این فهرست نیست. اولین مورد را از بالا اضافه کنید.
        </p>
        <ul class="divide-y">
          <li v-for="(o, i) in items" :key="o.id" class="flex items-center gap-2 px-3 py-2.5">
            <div class="flex flex-col">
              <button
                type="button"
                class="text-muted-foreground hover:text-foreground disabled:opacity-30"
                :disabled="busy || i === 0"
                aria-label="انتقال به بالا"
                @click="move(i, -1)"
              >
                <Icon name="lucide:chevron-up" class="size-4" />
              </button>
              <button
                type="button"
                class="text-muted-foreground hover:text-foreground disabled:opacity-30"
                :disabled="busy || i === items.length - 1"
                aria-label="انتقال به پایین"
                @click="move(i, 1)"
              >
                <Icon name="lucide:chevron-down" class="size-4" />
              </button>
            </div>

            <div class="min-w-0 flex-1">
              <form v-if="editingId === o.id" class="flex gap-2" @submit.prevent="saveRename(o)">
                <Input
                  v-model="editName"
                  dir="auto"
                  class="h-8"
                  maxlength="255"
                  autofocus
                  @keydown.esc="editingId = null"
                />
                <Button type="submit" size="sm" :disabled="busy || !editName.trim()">ذخیره</Button>
                <Button type="button" size="sm" variant="ghost" @click="editingId = null">انصراف</Button>
              </form>
              <template v-else>
                <p class="truncate" :class="{ 'text-muted-foreground line-through': !o.is_active }" dir="auto">
                  {{ o.name }}
                </p>
                <p v-if="!o.is_active" class="text-xs text-muted-foreground">در فرم مشتری نمایش داده نمی‌شود</p>
              </template>
            </div>

            <div v-if="editingId !== o.id" class="flex shrink-0 gap-0.5">
              <Button
                variant="ghost"
                size="icon"
                class="size-8"
                :title="o.is_active ? 'مخفی کردن از گزینه‌ها' : 'نمایش در گزینه‌ها'"
                :aria-label="o.is_active ? 'مخفی کردن از گزینه‌ها' : 'نمایش در گزینه‌ها'"
                :disabled="busy"
                @click="toggle(o)"
              >
                <Icon :name="o.is_active ? 'lucide:eye' : 'lucide:eye-off'" class="size-4" />
              </Button>
              <Button
                variant="ghost"
                size="icon"
                class="size-8"
                title="تغییر نام"
                aria-label="تغییر نام"
                :disabled="busy"
                @click="startRename(o)"
              >
                <Icon name="lucide:pencil" class="size-4" />
              </Button>
              <Button
                variant="ghost"
                size="icon"
                class="size-8 text-destructive hover:text-destructive"
                title="حذف"
                aria-label="حذف"
                :disabled="busy"
                @click="remove(o)"
              >
                <Icon name="lucide:trash-2" class="size-4" />
              </Button>
            </div>
          </li>
        </ul>
      </div>

      <DialogFooter class="border-t bg-muted/30 px-6 py-3">
        <p class="ml-auto self-center text-xs text-muted-foreground">
          تغییر نام روی مشتریان فعلی هم اعمال می‌شود. حذف، فقط این نام را از گزینه‌های قابل انتخاب برمی‌دارد و مشتریانی که قبلاً آن را دارند، مقدارشان حفظ می‌شود.
        </p>
        <Button variant="outline" @click="emit('update:open', false)">انجام شد</Button>
      </DialogFooter>
    </DialogContent>
  </Dialog>
</template>

<script setup lang="ts">
import { ApiError } from '~/services/backendApi'
import type { OptionItem, OptionKind } from '~/stores/customer'

const props = defineProps<{ open: boolean }>()
const emit = defineEmits<{ 'update:open': [value: boolean], 'changed': [] }>()

const store = useCustomerStore()
const notify = useNotify()

const tabs: { kind: OptionKind, label: string }[] = [
  { kind: 'PRODUCT', label: 'نام محصول' },
  { kind: 'GRADE', label: 'نام گرید' },
]
const kind = ref<OptionKind>('PRODUCT')
const newName = ref('')
const editingId = ref<number | null>(null)
const editName = ref('')
const busy = ref(false)
let dirty = false // something changed -> tell the page once when the dialog closes

const byOrder = (a: OptionItem, b: OptionItem) => a.sort_order - b.sort_order || a.name.localeCompare(b.name)
const itemsOf = (k: OptionKind) => store.optionItems.filter(o => o.kind === k).sort(byOrder)
const items = computed(() => itemsOf(kind.value))
const countOf = (k: OptionKind) => store.optionItems.filter(o => o.kind === k).length

function switchKind(k: OptionKind) {
  kind.value = k
  editingId.value = null
  newName.value = ''
}

watch(() => props.open, (isOpen) => {
  if (isOpen) {
    editingId.value = null
    newName.value = ''
    dirty = false
    store.loadOptionItems()
  }
  else if (dirty) {
    dirty = false
    emit('changed') // renames are applied to customers server-side, so refresh the table
  }
}, { immediate: true })

async function run(fn: () => Promise<unknown>, fallback: string) {
  busy.value = true
  try {
    await fn()
    dirty = true
  }
  catch (e) {
    notify.error(e instanceof ApiError ? e.message : fallback)
  }
  finally {
    busy.value = false
  }
}

const add = () => run(async () => {
  const name = newName.value.trim().replace(/\s+/g, ' ')
  if (!name) return
  await store.addOptionItem(kind.value, name)
  notify.success('گزینه اضافه شد.')
  newName.value = '' // stay open: several are usually added in a row
}, 'افزودن گزینه انجام نشد.')

function startRename(o: OptionItem) {
  editingId.value = o.id
  editName.value = o.name
}
const saveRename = (o: OptionItem) => run(async () => {
  const name = editName.value.trim().replace(/\s+/g, ' ')
  if (name && name !== o.name) {
    await store.updateOptionItem(o.id, { name })
    notify.success('نام تغییر کرد و روی مشتریان فعلی هم اعمال شد.')
  }
  editingId.value = null
}, 'تغییر نام انجام نشد.')

const toggle = (o: OptionItem) =>
  run(() => store.updateOptionItem(o.id, { is_active: !o.is_active }), 'به‌روزرسانی گزینه انجام نشد.')

function remove(o: OptionItem) {
  if (!window.confirm(`«${o.name}» از فهرست حذف شود؟\nمشتریانی که قبلاً این مقدار را دارند، آن را نگه می‌دارند.`)) return
  return run(async () => {
    await store.removeOptionItem(o.id)
    notify.success('گزینه حذف شد.')
  }, 'حذف گزینه انجام نشد.')
}

// swap with the neighbour; orders are renumbered 1..n first so a swap is always between two distinct values
const move = (i: number, dir: -1 | 1) => run(async () => {
  const list = [...items.value]
  const j = i + dir
  if (j < 0 || j >= list.length) return
  ;[list[i], list[j]] = [list[j]!, list[i]!]
  await Promise.all(list.map((x, idx) => (x.sort_order === idx + 1 ? null : store.updateOptionItem(x.id, { sort_order: idx + 1 }))))
}, 'جابه‌جایی انجام نشد.')
</script>
