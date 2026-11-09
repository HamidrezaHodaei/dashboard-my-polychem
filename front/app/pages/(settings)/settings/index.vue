<template>
  <div
    dir="rtl"
    class="space-y-6 text-right"
  >
    <!-- Appearance -->
    <Card class="shadow-none">
      <CardHeader>
        <CardTitle>ظاهر برنامه</CardTitle>
        <CardDescription>حالت روشن، تاریک یا هماهنگ با سیستم‌عامل را انتخاب کنید.</CardDescription>
      </CardHeader>
      <CardContent>
        <ColorModeSelect />
      </CardContent>
    </Card>

    <!-- Profile -->
    <Card class="shadow-none">
      <CardHeader>
        <CardTitle>پروفایل</CardTitle>
        <CardDescription>
          نام، ایمیل، نام کاربری و نقش‌ها از سامانه خوانده می‌شود و فقط مدیر سیستم می‌تواند آن‌ها را تغییر دهد. عکس پروفایل را می‌توانید خودتان عوض کنید.
        </CardDescription>
      </CardHeader>
      <CardContent class="space-y-6">
        <div class="flex flex-wrap items-center gap-4">
          <Avatar class="size-20 border border-input bg-input/30">
            <AvatarImage
              v-if="user?.avatar"
              :src="user.avatar"
              alt="عکس پروفایل"
            />
            <AvatarFallback class="text-lg">
              {{ initials }}
            </AvatarFallback>
          </Avatar>
          <div class="space-y-2">
            <div class="flex flex-wrap gap-2">
              <input
                ref="fileInput"
                type="file"
                accept="image/png,image/jpeg,image/webp"
                class="sr-only"
                @change="onPick"
              >
              <Button
                type="button"
                variant="outline"
                class="gap-2"
                :disabled="busy"
                @click="fileInput?.click()"
              >
                <Icon
                  name="lucide:image-up"
                  class="size-4"
                />
                {{ busy ? 'در حال بارگذاری...' : 'تغییر عکس' }}
              </Button>
              <Button
                v-if="user?.avatar"
                type="button"
                variant="ghost"
                class="gap-2 text-destructive"
                :disabled="busy"
                @click="removeAvatar"
              >
                <Icon
                  name="lucide:trash-2"
                  class="size-4"
                />
                حذف عکس
              </Button>
            </div>
            <p class="text-xs text-muted-foreground">
              فرمت PNG، JPEG یا WebP؛ تصویر خودکار به اندازه‌ی مناسب کوچک می‌شود.
            </p>
          </div>
        </div>

        <div class="grid gap-4 md:grid-cols-2">
          <div class="space-y-1.5">
            <Label>نام و نام خانوادگی</Label>
            <Input
              :model-value="user?.full_name ?? ''"
              dir="auto"
              readonly
              class="bg-muted/40"
            />
          </div>
          <div class="space-y-1.5">
            <Label>نام کاربری</Label>
            <Input
              :model-value="user?.username ?? ''"
              dir="ltr"
              readonly
              class="bg-muted/40 text-left"
            />
          </div>
          <div class="space-y-1.5 md:col-span-2">
            <Label>ایمیل</Label>
            <Input
              :model-value="user?.email ?? ''"
              dir="ltr"
              readonly
              class="bg-muted/40 text-left"
            />
          </div>
          <div class="space-y-1.5 md:col-span-2">
            <Label>نقش‌ها</Label>
            <div class="flex min-h-10 flex-wrap items-center gap-2 rounded-md border bg-muted/40 px-3 py-2">
              <Badge
                v-for="r in user?.roles ?? []"
                :key="r.name"
                variant="secondary"
              >
                {{ r.display_name || r.name }}
              </Badge>
              <span
                v-if="!(user?.roles ?? []).length"
                class="text-sm text-muted-foreground"
              >نقشی برای شما تعریف نشده است.</span>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  </div>
</template>

<script lang="ts" setup>
import { ApiError } from '~/services/backendApi'

usePageSeoMeta({ title: 'تنظیمات عمومی' })

const auth = useAuthStore()
const notify = useNotify()
const user = computed(() => auth.user)
const fileInput = ref<HTMLInputElement | null>(null)
const busy = ref(false)

const initials = computed(() => (user.value?.full_name ?? '').trim().split(/\s+/).map(p => p[0]).join('').slice(0, 2) || '؟')

/** Centre-crop to a square and shrink to 256px: a few tens of KB, whatever the camera produced. */
async function toAvatarDataUrl(file: File): Promise<string> {
  const bitmap = await createImageBitmap(file)
  const size = 256
  const canvas = document.createElement('canvas')
  canvas.width = canvas.height = size
  const side = Math.min(bitmap.width, bitmap.height)
  const ctx = canvas.getContext('2d')!
  ctx.fillStyle = '#fff'
  ctx.fillRect(0, 0, size, size)
  ctx.drawImage(bitmap, (bitmap.width - side) / 2, (bitmap.height - side) / 2, side, side, 0, 0, size, size)
  return canvas.toDataURL('image/jpeg', 0.85)
}

async function onPick(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = '' // allow picking the same file again
  if (!file) return
  if (!['image/png', 'image/jpeg', 'image/webp'].includes(file.type)) {
    return notify.error('فقط تصویر PNG، JPEG یا WebP قابل قبول است')
  }
  if (file.size > 10 * 1024 * 1024) return notify.error('حجم تصویر نباید بیشتر از ۱۰ مگابایت باشد')
  busy.value = true
  try {
    await auth.setAvatar(await toAvatarDataUrl(file))
    notify.success('عکس پروفایل به‌روزرسانی شد')
  }
  catch (err) {
    notify.error(err instanceof ApiError ? 'ذخیره‌ی عکس انجام نشد؛ تصویر دیگری را امتحان کنید' : 'پردازش تصویر انجام نشد')
  }
  finally {
    busy.value = false
  }
}

async function removeAvatar() {
  busy.value = true
  try {
    await auth.setAvatar(null)
    notify.success('عکس پروفایل حذف شد')
  }
  catch {
    notify.error('حذف عکس انجام نشد')
  }
  finally {
    busy.value = false
  }
}
</script>
