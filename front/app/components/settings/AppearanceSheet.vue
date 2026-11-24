<template>
  <Sheet>
    <SheetTrigger as-child>
      <Button
        variant="ghost"
        size="icon"
        aria-label="شخصی‌سازی ظاهر"
      >
        <Icon
          name="lucide:sliders-horizontal"
          class="text-lg size-5"
          aria-hidden="true"
        />
      </Button>
    </SheetTrigger>

    <SheetContent
      side="left"
      dir="rtl"
      class="w-full overflow-y-auto sm:max-w-sm"
    >
      <SheetHeader>
        <SheetTitle>شخصی‌سازی ظاهر</SheetTitle>
        <SheetDescription>
          رنگ سازمانی و فونت ثابت می‌مانند؛ انتخاب‌های شما در همین مرورگر ذخیره می‌شود.
        </SheetDescription>
      </SheetHeader>

      <div class="flex flex-col gap-7 px-4 pb-6">
        <!-- Light / dark / system -->
        <section aria-labelledby="ap-mode">
          <h3
            id="ap-mode"
            class="mb-2 text-sm font-medium"
          >
            حالت رنگ
          </h3>
          <div
            role="radiogroup"
            aria-labelledby="ap-mode"
            class="grid grid-cols-3 gap-2"
          >
            <button
              v-for="m in modes"
              :key="m.value"
              type="button"
              role="radio"
              :aria-checked="colorMode.preference === m.value"
              :class="optionClass(colorMode.preference === m.value)"
              @click="setColorMode(m.value, $event)"
            >
              {{ m.label }}
            </button>
          </div>
        </section>

        <!-- Palette -->
        <section aria-labelledby="ap-palette">
          <h3
            id="ap-palette"
            class="mb-2 text-sm font-medium"
          >
            پالت رنگی
          </h3>
          <div
            role="radiogroup"
            aria-labelledby="ap-palette"
            class="grid grid-cols-3 gap-2"
          >
            <button
              v-for="p in PALETTES"
              :key="p.id"
              type="button"
              role="radio"
              :aria-checked="palette === p.id"
              :class="optionClass(palette === p.id, 'flex-col gap-2 py-3')"
              @click="setPalette(p.id, $event)"
            >
              <span
                class="relative flex h-9 w-full overflow-hidden rounded-md border"
                :style="{ background: swatch(p)[0] }"
                aria-hidden="true"
              >
                <span
                  class="absolute inset-y-0 start-0 w-1/3"
                  :style="{ background: swatch(p)[1] }"
                />
                <!-- brand yellow: identical in every palette -->
                <span class="absolute bottom-1.5 end-1.5 size-3 rounded-full bg-primary ring-1 ring-black/10" />
              </span>
              {{ p.label }}
            </button>
          </div>
        </section>

        <!-- Sidebar style -->
        <section aria-labelledby="ap-sidebar">
          <h3
            id="ap-sidebar"
            class="mb-2 text-sm font-medium"
          >
            سبک سایدبار
          </h3>
          <div
            role="radiogroup"
            aria-labelledby="ap-sidebar"
            class="grid grid-cols-3 gap-2"
          >
            <button
              v-for="v in SIDEBAR_VARIANTS"
              :key="v.id"
              type="button"
              role="radio"
              :aria-checked="sidebarVariant === v.id"
              :class="optionClass(sidebarVariant === v.id, 'flex-col gap-2 py-3')"
              @click="setSidebarVariant(v.id)"
            >
              <span
                class="relative block h-9 w-full overflow-hidden rounded-md border bg-muted"
                aria-hidden="true"
              >
                <!-- sidebar sits on the right (RTL) -->
                <span
                  v-if="v.id === 'sidebar'"
                  class="absolute inset-y-0 end-0 w-3 border-s bg-background"
                />
                <span
                  v-else-if="v.id === 'floating'"
                  class="absolute inset-y-1 end-1 w-3 rounded-sm border bg-background shadow-sm"
                />
                <template v-else>
                  <span class="absolute inset-y-0 end-0 w-4 bg-sidebar" />
                  <span class="absolute inset-y-1 start-1 end-5 rounded-sm border bg-background" />
                </template>
              </span>
              {{ v.label }}
            </button>
          </div>
        </section>

        <!-- Content width -->
        <section aria-labelledby="ap-width">
          <h3
            id="ap-width"
            class="mb-2 text-sm font-medium"
          >
            عرض محتوا
          </h3>
          <div
            role="radiogroup"
            aria-labelledby="ap-width"
            class="grid grid-cols-2 gap-2"
          >
            <button
              v-for="w in CONTENT_WIDTHS"
              :key="w.id"
              type="button"
              role="radio"
              :aria-checked="contentWidth === w.id"
              :class="optionClass(contentWidth === w.id, 'flex-col gap-2 py-3')"
              @click="setContentWidth(w.id)"
            >
              <span
                class="flex h-9 w-full items-center justify-center rounded-md border bg-muted"
                aria-hidden="true"
              >
                <span
                  class="h-6 rounded-sm border bg-background"
                  :class="w.id === 'fluid' ? 'w-[calc(100%-0.5rem)]' : 'w-1/2'"
                />
              </span>
              {{ w.label }}
            </button>
          </div>
        </section>

        <Button
          variant="outline"
          class="w-full"
          @click="reset($event)"
        >
          بازنشانی به پیش‌فرض
        </Button>
      </div>
    </SheetContent>
  </Sheet>
</template>

<script lang="ts" setup>
import { cn } from '@/utils/lib/utils'

const { colorMode, setColorMode } = useThemeTransition()
const { palette, sidebarVariant, contentWidth, setPalette, setSidebarVariant, setContentWidth, reset }
  = useAppearance()

const modes = [
  { label: 'سیستم', value: 'system' },
  { label: 'روشن', value: 'light' },
  { label: 'تاریک', value: 'dark' },
] as const

const swatch = (p: typeof PALETTES[number]) => (colorMode.value === 'dark' ? p.dark : p.light)

const optionClass = (active: boolean, extra = 'gap-2 py-2') => cn(
  'flex items-center justify-center rounded-lg border px-2 text-xs transition-colors',
  'hover:bg-accent focus-visible:outline-2 focus-visible:outline-ring',
  active ? 'border-primary ring-2 ring-primary/60 bg-accent font-medium' : 'border-border',
  extra,
)
</script>
