<!--/components/mail/UnitAccessDialog.vue → <MailUnitAccessDialog /> : which organizational units may use correspondence -->
<script setup lang="ts">
import { ApiError, apiFetch } from '~/services/backendApi'

const props = defineProps<{ open: boolean }>()
const emit = defineEmits<{ 'update:open': [boolean] }>()
const notify = useNotify()

interface Unit { id: number, name: string, enabled: boolean, member_count: number }
const units = ref<Unit[]>([])
const selected = ref<Set<number>>(new Set())
const loading = ref(false)
const saving = ref(false)

watch(() => props.open, async (v) => {
  if (!v) return
  loading.value = true
  try {
    units.value = await apiFetch<Unit[]>('/mail/access/units')
    selected.value = new Set(units.value.filter(u => u.enabled).map(u => u.id))
  }
  catch (e) { notify.error('بارگذاری واحدها ناموفق بود.', e instanceof ApiError ? e.message : undefined) }
  finally { loading.value = false }
})
function toggle(id: number, on: boolean) {
  const next = new Set(selected.value)
  if (on) next.add(id)
  else next.delete(id)
  selected.value = next
}
async function save() {
  saving.value = true
  try {
    await apiFetch('/mail/access/units', { method: 'PUT', body: { department_ids: [...selected.value] } })
    notify.success('دسترسی واحدها به مکاتبات ذخیره شد.')
    emit('update:open', false)
  }
  catch (e) { notify.error('ذخیره ناموفق بود.', e instanceof ApiError ? e.message : undefined) }
  finally { saving.value = false }
}
</script>

<template>
  <Dialog :open="open" @update:open="v => emit('update:open', v)">
    <DialogContent dir="rtl" class="flex max-h-[85vh] flex-col gap-0 overflow-hidden p-0 sm:max-w-lg">
      <DialogHeader class="border-b px-6 py-4 text-right">
        <DialogTitle class="text-lg font-semibold">
          دسترسی واحدهای سازمانی به مکاتبات
        </DialogTitle>
        <DialogDescription>
          اعضای واحدهای فعال (و تیم‌های آن‌ها) می‌توانند از مکاتبات استفاده کنند. دسترسی کاربران و نقش‌ها جداگانه از «ماتریس مجوزها» تنظیم می‌شود.
        </DialogDescription>
      </DialogHeader>
      <div class="flex-1 overflow-y-auto px-3 py-2">
        <p v-if="loading" class="p-6 text-center text-sm text-muted-foreground">
          در حال بارگذاری…
        </p>
        <p v-else-if="!units.length" class="p-6 text-center text-sm text-muted-foreground">
          واحد سازمانی ثبت نشده است.
        </p>
        <label
          v-for="u in units"
          :key="u.id"
          class="flex cursor-pointer items-center gap-3 rounded-md px-3 py-2.5 hover:bg-accent"
        >
          <Switch :model-value="selected.has(u.id)" @update:model-value="v => toggle(u.id, !!v)" />
          <span class="flex-1 text-sm">{{ u.name }}</span>
          <span class="text-xs text-muted-foreground">{{ u.member_count.toLocaleString('fa-IR') }} کاربر فعال</span>
        </label>
      </div>
      <div class="flex justify-end gap-2 border-t px-6 py-3">
        <Button variant="outline" @click="emit('update:open', false)">
          انصراف
        </Button>
        <Button :disabled="saving || loading" @click="save">
          ذخیره
        </Button>
      </div>
    </DialogContent>
  </Dialog>
</template>
