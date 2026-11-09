<!--/components/customer/CategoriesDialog.vue  → <CustomerCategoriesDialog /> -->
<template>
  <Dialog :open="open" @update:open="v => emit('update:open', v)">
    <DialogContent class="flex max-h-[85vh] flex-col gap-0 overflow-hidden p-0 sm:max-w-xl">
      <DialogHeader class="border-b px-6 py-4 text-right">
        <DialogTitle class="text-lg font-semibold">
          صنعت فعالیت مشتریان
        </DialogTitle>
        <DialogDescription>
          این موارد در فهرست «صنعت فعالیت» فرم مشتری نمایش داده می‌شوند؛ هر صنعت اصلی می‌تواند چند صنعت فرعی داشته باشد.
        </DialogDescription>
      </DialogHeader>

      <form
        class="flex gap-2 border-b px-6 py-4"
        @submit.prevent="add"
      >
        <Input
          v-model="newName"
          dir="auto"
          placeholder="نام صنعت اصلی جدید"
          maxlength="100"
          :disabled="busy"
        />
        <Button
          type="submit"
          class="gap-1.5"
          :disabled="busy || !newName.trim()"
        >
          <Icon
            name="lucide:plus"
            class="size-4"
          /> افزودن
        </Button>
      </form>

      <div class="flex-1 overflow-y-auto px-3 py-2">
        <p
          v-if="!store.categoryItems.length"
          class="p-6 text-center text-sm text-muted-foreground"
        >
          هنوز دسته‌بندی‌ای وجود ندارد. اولین مورد را از بالا اضافه کنید؛ تا آن زمان صنعت مشتری قابل انتخاب نیست.
        </p>

        <ul class="divide-y">
          <li
            v-for="r in rows"
            :key="r.key"
            class="px-3"
            :class="(r.type === 'item' && r.c.parent_id) || r.type === 'add' ? 'ms-6 border-s-2' : ''"
          >
            <!-- inline "add sub-category" form -->
            <form
              v-if="r.type === 'add'"
              class="flex gap-2 py-2.5"
              @submit.prevent="addSub(r.parent)"
            >
              <Input
                v-model="subName"
                dir="auto"
                class="h-8"
                maxlength="100"
                :placeholder="`صنعت فرعی جدید برای «${r.parent.name}»`"
                autofocus
                @keydown.esc="addingUnder = null"
              />
              <Button
                type="submit"
                size="sm"
                :disabled="busy || !subName.trim()"
              >
                افزودن
              </Button>
              <Button
                type="button"
                size="sm"
                variant="ghost"
                @click="addingUnder = null"
              >
                انصراف
              </Button>
            </form>

            <div
              v-else
              class="flex items-center gap-2 py-2.5"
            >
              <div class="flex flex-col">
                <button
                  type="button"
                  class="text-muted-foreground hover:text-foreground disabled:opacity-30"
                  :disabled="busy || r.index === 0"
                  aria-label="انتقال به بالا"
                  @click="move(r.c, -1)"
                >
                  <Icon
                    name="lucide:chevron-up"
                    class="size-4"
                  />
                </button>
                <button
                  type="button"
                  class="text-muted-foreground hover:text-foreground disabled:opacity-30"
                  :disabled="busy || r.index === r.count - 1"
                  aria-label="انتقال به پایین"
                  @click="move(r.c, 1)"
                >
                  <Icon
                    name="lucide:chevron-down"
                    class="size-4"
                  />
                </button>
              </div>

              <div class="min-w-0 flex-1">
                <form
                  v-if="editingId === r.c.id"
                  class="flex gap-2"
                  @submit.prevent="saveRename(r.c)"
                >
                  <Input
                    v-model="editName"
                    dir="auto"
                    class="h-8"
                    maxlength="100"
                    autofocus
                    @keydown.esc="editingId = null"
                  />
                  <Button
                    type="submit"
                    size="sm"
                    :disabled="busy || !editName.trim()"
                  >
                    ذخیره
                  </Button>
                  <Button
                    type="button"
                    size="sm"
                    variant="ghost"
                    @click="editingId = null"
                  >
                    انصراف
                  </Button>
                </form>
                <template v-else>
                  <p
                    class="truncate"
                    :class="[r.c.parent_id ? 'text-sm' : 'font-medium', { 'text-muted-foreground line-through': !r.c.is_active }]"
                    dir="auto"
                  >
                    {{ r.c.name }}
                  </p>
                  <p class="text-xs text-muted-foreground">
                    {{ r.c.customer_count }} مشتری
                    <span v-if="!r.c.parent_id && r.childCount"> · {{ r.childCount }} دسته‌بندی فرعی</span>
                    <span v-if="!r.c.is_active"> · در فرم مشتری نمایش داده نمی‌شود</span>
                  </p>
                </template>
              </div>

              <div
                v-if="editingId !== r.c.id"
                class="flex shrink-0 gap-0.5"
              >
                <Button
                  v-if="!r.c.parent_id"
                  variant="ghost"
                  size="icon"
                  class="size-8"
                  title="افزودن دسته‌بندی فرعی"
                  aria-label="افزودن دسته‌بندی فرعی"
                  :disabled="busy"
                  @click="startAddSub(r.c)"
                >
                  <Icon
                    name="lucide:corner-down-left"
                    class="size-4"
                  />
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  class="size-8"
                  :title="r.c.is_active ? 'مخفی کردن از گزینه‌ها' : 'نمایش در گزینه‌ها'"
                  :aria-label="r.c.is_active ? 'مخفی کردن از گزینه‌ها' : 'نمایش در گزینه‌ها'"
                  :disabled="busy"
                  @click="toggle(r.c)"
                >
                  <Icon
                    :name="r.c.is_active ? 'lucide:eye' : 'lucide:eye-off'"
                    class="size-4"
                  />
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  class="size-8"
                  title="تغییر نام"
                  aria-label="تغییر نام"
                  :disabled="busy"
                  @click="startRename(r.c)"
                >
                  <Icon
                    name="lucide:pencil"
                    class="size-4"
                  />
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  class="size-8 text-destructive hover:text-destructive"
                  title="حذف"
                  aria-label="حذف"
                  :disabled="busy"
                  @click="remove(r.c, r.childCount)"
                >
                  <Icon
                    name="lucide:trash-2"
                    class="size-4"
                  />
                </Button>
              </div>
            </div>
          </li>
        </ul>
      </div>

      <DialogFooter class="border-t bg-muted/30 px-6 py-3">
        <p class="ml-auto self-center text-xs text-muted-foreground">
          تغییر نام روی مشتریان فعلی نیز اعمال می‌شود. حذف، فقط این نام (و زیرمجموعه‌هایش) را از گزینه‌های قابل انتخاب برمی‌دارد.
        </p>
        <Button
          variant="outline"
          @click="emit('update:open', false)"
        >
          انجام شد
        </Button>
      </DialogFooter>
    </DialogContent>
  </Dialog>
</template>

<script setup lang="ts">
const notify = useNotify()
import { ApiError } from '~/services/backendApi'

type Item = { id: number, name: string, parent_id: number | null, is_active: boolean, sort_order: number, customer_count: number }
type Row
  = | { type: 'item', key: string, c: Item, index: number, count: number, childCount: number }
    | { type: 'add', key: string, parent: Item }

const props = defineProps<{ open: boolean }>()
const emit = defineEmits<{ 'update:open': [value: boolean], 'changed': [] }>()

const store = useCustomerStore()
const newName = ref('')
const subName = ref('')
const addingUnder = ref<number | null>(null)
const editingId = ref<number | null>(null)
const editName = ref('')
const busy = ref(false)

const byOrder = (a: Item, b: Item) => a.sort_order - b.sort_order || a.name.localeCompare(b.name)
const roots = computed(() => (store.categoryItems as Item[]).filter(c => !c.parent_id).sort(byOrder))
const childrenOf = (id: number) => (store.categoryItems as Item[]).filter(c => c.parent_id === id).sort(byOrder)

// Flat render list: each main category, its sub-categories, and (when open)
// the inline "add sub-category" form at the end of that group.
const rows = computed<Row[]>(() => {
  const out: Row[] = []
  roots.value.forEach((root, i) => {
    const kids = childrenOf(root.id)
    out.push({ type: 'item', key: `c${root.id}`, c: root, index: i, count: roots.value.length, childCount: kids.length })
    kids.forEach((k, j) => out.push({ type: 'item', key: `c${k.id}`, c: k, index: j, count: kids.length, childCount: 0 }))
    if (addingUnder.value === root.id) out.push({ type: 'add', key: `a${root.id}`, parent: root })
  })
  return out
})

watch(() => props.open, (v) => {
  if (v) {
    editingId.value = null
    addingUnder.value = null
    newName.value = ''
    subName.value = ''
    store.loadCategoryItems().catch(() => notify.error('بارگیری دسته‌بندی‌ها انجام نشد.'))
  }
}, { immediate: true })

async function run(fn: () => Promise<unknown>, fallback: string) {
  busy.value = true
  try {
    await fn()
    // keep the panel's filter dropdowns and the wizard's selects in step
    await Promise.all([store.loadCategoryItems(), store.loadCategories()])
    emit('changed')
  }
  catch (e) {
    notify.error(e instanceof ApiError ? e.message : fallback)
  }
  finally {
    busy.value = false
  }
}

const add = () => run(async () => {
  await store.addCategory(newName.value.trim())
  notify.success('دسته‌بندی اصلی اضافه شد.')
  newName.value = ''
}, 'افزودن دسته‌بندی انجام نشد.')

function startAddSub(parent: Item) {
  editingId.value = null
  subName.value = ''
  addingUnder.value = parent.id
}
const addSub = (parent: Item) => run(async () => {
  await store.addCategory(subName.value.trim(), parent.id)
  notify.success('دسته‌بندی فرعی اضافه شد.')
  subName.value = '' // stay open: admins usually add several in a row
}, 'افزودن دسته‌بندی فرعی انجام نشد.')

function startRename(c: Item) {
  addingUnder.value = null
  editingId.value = c.id
  editName.value = c.name
}
const saveRename = (c: Item) => run(async () => {
  if (editName.value.trim() !== c.name) {
    await store.updateCategory(c.id, { name: editName.value.trim() })
    notify.success('نام دسته‌بندی تغییر کرد.')
  }
  editingId.value = null
}, 'تغییر نام دسته‌بندی انجام نشد.')

const toggle = (c: Item) =>
  run(() => store.updateCategory(c.id, { is_active: !c.is_active }), 'به‌روزرسانی دسته‌بندی انجام نشد.')

function remove(c: Item, childCount: number) {
  const parts: string[] = []
  if (childCount) parts.push(`${childCount} دسته‌بندی فرعی این مورد نیز از گزینه‌ها حذف می‌شود.`)
  if (c.customer_count) parts.push(`${c.customer_count} مشتری فعلی این دسته‌بندی را در اطلاعات خود دارند، اما دیگر به‌عنوان گزینه نمایش داده نمی‌شود.`)
  const extra = parts.length ? `\n\n${parts.join('\n')}` : ''
  if (!window.confirm(`دسته‌بندی «${c.name}» حذف شود؟${extra}`)) return
  return run(async () => {
    await store.removeCategory(c.id)
    notify.success('دسته‌بندی حذف شد.')
  }, 'حذف دسته‌بندی انجام نشد.')
}

// Swap with the neighbour *among its siblings* (same parent). Sibling orders
// are renumbered 1..n first so a swap is always between two distinct values.
const move = (c: Item, dir: -1 | 1) => run(async () => {
  const list = [...(c.parent_id ? childrenOf(c.parent_id) : roots.value)]
  const i = list.findIndex(x => x.id === c.id)
  const j = i + dir
  if (i < 0 || j < 0 || j >= list.length) return
  ;[list[i], list[j]] = [list[j], list[i]]
  await Promise.all(
    list.map((x, idx) => (x.sort_order === idx + 1 ? null : store.updateCategory(x.id, { sort_order: idx + 1 }))),
  )
}, 'مرتب‌سازی دسته‌بندی‌ها انجام نشد.')
</script>