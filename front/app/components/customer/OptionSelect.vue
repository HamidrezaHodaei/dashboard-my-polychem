<!-- /components/customer/OptionSelect.vue  → <CustomerOptionSelect />
     یک select که گزینه‌ها را از دیتابیس می‌گیرد (نام محصول یا نام گرید) و کاربر می‌تواند
     همان‌جا گزینه‌ی جدید اضافه و انتخاب کند. -->
<template>
  <div class="space-y-1.5">
    <div class="flex items-center gap-1">
      <Select
        :model-value="adding ? ADD : (modelValue || NONE)"
        @update:model-value="onPick"
      >
        <SelectTrigger class="w-full min-w-0" :aria-invalid="invalid">
          <SelectValue :placeholder="placeholder || 'انتخاب کنید'" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem :value="NONE">انتخاب کنید...</SelectItem>
          <SelectItem v-for="n in choices" :key="n" :value="n">{{ n }}</SelectItem>
          <SelectItem :value="ADD">＋ افزودن گزینه‌ی جدید</SelectItem>
        </SelectContent>
      </Select>
      <!-- edit / delete the selected entry of the pick-list (stored in the database) -->
      <template v-if="selectedItem">
        <Button
          type="button"
          variant="ghost"
          size="icon"
          class="size-8 shrink-0 text-muted-foreground"
          title="ویرایش نام این گزینه"
          aria-label="ویرایش نام این گزینه"
          :disabled="busy"
          @click="startEdit"
        >
          <Icon name="lucide:pencil" class="size-4" />
        </Button>
        <Button
          type="button"
          variant="ghost"
          size="icon"
          class="size-8 shrink-0 text-muted-foreground hover:text-destructive"
          title="حذف این گزینه از فهرست"
          aria-label="حذف این گزینه از فهرست"
          :disabled="busy"
          @click="removeSelected"
        >
          <Icon name="lucide:trash-2" class="size-4" />
        </Button>
      </template>
    </div>

    <form v-if="editing && selectedItem" class="flex gap-2" @submit.prevent="saveEdit">
      <Input
        v-model="editName"
        dir="auto"
        class="h-8"
        maxlength="255"
        placeholder="نام جدید"
        autofocus
        @keydown.esc="editing = false"
      />
      <Button type="submit" size="sm" :disabled="busy || !editName.trim()">ذخیره</Button>
      <Button type="button" size="sm" variant="ghost" @click="editing = false">انصراف</Button>
    </form>

    <form v-if="adding" class="flex gap-2" @submit.prevent="addNew">
      <Input
        v-model="newName"
        dir="auto"
        class="h-8"
        maxlength="255"
        :placeholder="kind === 'GRADE' ? 'نام گرید جدید' : 'نام محصول جدید'"
        autofocus
        @keydown.esc="adding = false"
      />
      <Button type="submit" size="sm" :disabled="busy || !newName.trim()">افزودن</Button>
      <Button type="button" size="sm" variant="ghost" @click="adding = false">انصراف</Button>
    </form>
  </div>
</template>

<script setup lang="ts">
import { ApiError } from '~/services/backendApi'
import type { OptionKind } from '~/stores/customer'

const props = defineProps<{
  modelValue: string
  kind: OptionKind
  placeholder?: string
  invalid?: boolean
}>()
const emit = defineEmits<{ 'update:modelValue': [value: string] }>()

const store = useCustomerStore()
const notify = useNotify()
const NONE = '__none__'
const ADD = '__add__'
const adding = ref(false)
const newName = ref('')
const busy = ref(false)
const editing = ref(false)
const editName = ref('')

// the database entry behind the currently selected name (if it is one)
const selectedItem = computed(() =>
  props.modelValue
    ? store.optionItems.find(o => o.kind === props.kind && o.name === props.modelValue) ?? null
    : null,
)

function startEdit() {
  if (!selectedItem.value) return
  adding.value = false
  editName.value = selectedItem.value.name
  editing.value = true
}

async function saveEdit() {
  const item = selectedItem.value
  const name = editName.value.trim().replace(/\s+/g, ' ')
  if (!item || !name) return
  if (name === item.name) { editing.value = false; return }
  busy.value = true
  try {
    await store.updateOptionItem(item.id, { name })
    emit('update:modelValue', name)
    editing.value = false
    notify.success('نام گزینه ویرایش شد.')
  }
  catch (e) {
    notify.error(e instanceof ApiError ? e.message : 'ویرایش گزینه انجام نشد.')
  }
  finally {
    busy.value = false
  }
}

async function removeSelected() {
  const item = selectedItem.value
  if (!item) return
  if (!window.confirm(`«${item.name}» از فهرست حذف شود؟ مشتریانی که قبلاً این مقدار را دارند، آن را حفظ می‌کنند.`)) return
  busy.value = true
  try {
    await store.removeOptionItem(item.id)
    editing.value = false
    emit('update:modelValue', '')
    notify.success('گزینه از فهرست حذف شد.')
  }
  catch (e) {
    notify.error(e instanceof ApiError ? e.message : 'حذف گزینه انجام نشد.')
  }
  finally {
    busy.value = false
  }
}

// active options of this kind; a value already saved on the customer always stays selectable
const choices = computed(() => {
  const names = store.optionItems.filter(o => o.kind === props.kind && o.is_active).map(o => o.name)
  return props.modelValue && !names.includes(props.modelValue) ? [props.modelValue, ...names] : names
})

function onPick(v: unknown) {
  const val = String(v)
  if (val === ADD) {
    adding.value = true
    newName.value = ''
    return
  }
  adding.value = false
  emit('update:modelValue', val === NONE ? '' : val)
}

async function addNew() {
  const name = newName.value.trim().replace(/\s+/g, ' ')
  if (!name) return
  busy.value = true
  try {
    const exists = store.optionItems.find(o => o.kind === props.kind && o.name === name)
    if (!exists) await store.addOptionItem(props.kind, name)
    emit('update:modelValue', name)
    adding.value = false
    newName.value = ''
  }
  catch (e) {
    notify.error(e instanceof ApiError ? e.message : 'افزودن گزینه انجام نشد.')
  }
  finally {
    busy.value = false
  }
}
</script>