<template>
  <main
    v-if="ready"
    class="relative mx-auto flex min-h-dvh w-full max-w-md flex-col bg-background px-6 text-foreground"
    style="padding-top: calc(env(safe-area-inset-top, 0px) + 1.25rem); padding-bottom: calc(env(safe-area-inset-bottom, 0px) + 1.5rem)"
  >
    <header class="flex h-10 items-center justify-center">
      <LogoSVG />
    </header>

    <section class="flex flex-1 flex-col justify-center py-8 text-center">
      <h1 class="text-4xl font-extrabold leading-[1.35]">
        سامانه یکپارچه پلیکم
        <span
          class="mt-1 grid text-[#878787] dark:text-neutral-400"
          translate="no"
          aria-label="پلیکم من"
        >
          <!-- نسخه نامرئی برای ثابت ماندن ابعاد -->
          <span
            class="invisible col-start-1 row-start-1"
            aria-hidden="true"
          >پلیکم من</span>
          <span
            class="col-start-1 row-start-1"
            aria-hidden="true"
          >
            <span v-text="typed" />
            <span class="caret" />
          </span>
        </span>
      </h1>

      <p class="mx-auto mt-6 max-w-sm text-base leading-8 text-muted-foreground">
        برای دسترسی آسان‌تر به خدمات و امکانات سامانه، نسخه موبایل را روی دستگاه خود نصب کنید.
      </p>

      <div class="mt-8 flex flex-col items-center gap-4">
        <Button
          size="lg"
          class="w-full max-w-xs"
          :disabled="busy || state === 'installed'"
          @click="onInstall"
        >
          {{ state === 'installed' ? 'نصب شد' : 'نصب اپلیکیشن' }}
        </Button>
        <Button
          variant="link"
          class="text-foreground"
          @click="continueInBrowser"
        >
          ورود از طریق مرورگر
          <Icon
            name="lucide:arrow-left"
            class="size-4"
            aria-hidden="true"
          />
        </Button>
      </div>

      <p
        v-if="state === 'declined'"
        role="status"
        class="mt-4 text-sm text-foreground"
      >
        نصب کامل نشد. هر زمان خواستید می‌توانید دوباره تلاش کنید.
      </p>
      <p
        v-else-if="state === 'installed'"
        role="status"
        class="mt-4 text-sm text-foreground"
      >
        اپلیکیشن نصب شد. آن را از صفحهٔ اصلی گوشی باز کنید.
      </p>

      <!-- Browsers without an install prompt (iOS Safari, Firefox, Samsung ...) -->
      <div
        v-if="state === 'manual'"
        role="region"
        aria-label="راهنمای نصب"
        class="mx-auto mt-5 w-full max-w-sm rounded-lg border bg-muted/30 p-4 text-start text-sm leading-7"
      >
        <p class="mb-1 font-semibold">
          نصب دستی
        </p>
        <ol
          v-if="pwa.isIos.value"
          class="list-decimal space-y-1 ps-5"
        >
          <li>در Safari دکمهٔ اشتراک‌گذاری را بزنید.</li>
          <li>گزینهٔ «افزودن به صفحهٔ اصلی» را انتخاب کنید.</li>
          <li>«افزودن» را بزنید و برنامه را از صفحهٔ اصلی باز کنید.</li>
        </ol>
        <ol
          v-else
          class="list-decimal space-y-1 ps-5"
        >
          <li>منوی مرورگر (سه‌نقطه) را باز کنید.</li>
          <li>«نصب برنامه» یا «افزودن به صفحهٔ اصلی» را بزنید.</li>
          <li>نصب را تأیید کنید.</li>
        </ol>
      </div>
    </section>

    <!-- App preview, drawn in CSS: no image to download on a mobile connection -->
    <div
      class="pointer-events-none mx-auto w-full max-w-xs select-none rounded-t-2xl border border-b-0 bg-card p-3 pb-0"
      aria-hidden="true"
    >
      <div class="mb-3 flex items-center gap-1.5">
        <span class="size-2 rounded-full bg-muted-foreground/30" />
        <span class="size-2 rounded-full bg-muted-foreground/30" />
        <span class="size-2 rounded-full bg-primary" />
      </div>
      <div class="space-y-2 pb-3">
        <div class="h-3 w-2/5 rounded bg-foreground/80" />
        <div class="grid grid-cols-3 gap-2">
          <div
            v-for="i in 3"
            :key="i"
            class="h-12 rounded-md bg-muted"
          />
        </div>
        <div class="h-3 w-full rounded bg-muted" />
        <div class="h-3 w-4/5 rounded bg-muted" />
      </div>
    </div>
  </main>
</template>

<script lang="ts" setup>
// Public landing page for installing the PWA on a phone. See middleware/01.install-gate.global.ts for who gets here.
definePageMeta({ layout: 'blank', public: true })
usePageSeoMeta({ title: 'نصب اپلیکیشن' })

const pwa = usePwa()
const ready = ref(false)
const busy = ref(false)
// idle: prompt available | manual: show instructions | declined / installed: after the browser prompt
const state = ref<'idle' | 'manual' | 'declined' | 'installed'>('idle')

// ---------- انیمیشن تایپ عنوان (مثل صفحه ورود) ----------
const fullTitle = 'پلیکم من'
const typed = ref('')
let typingTimer: ReturnType<typeof setTimeout> | undefined

function startTyping() {
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    typed.value = fullTitle
    return
  }

  const chars = Array.from(fullTitle)
  let index = 0
  let deleting = false

  const step = () => {
    if (!deleting) {
      index++
      typed.value = chars.slice(0, index).join('')
      if (index === chars.length) {
        deleting = true
        typingTimer = setTimeout(step, 2200)
        return
      }
      typingTimer = setTimeout(step, 170)
    }
    else {
      index--
      typed.value = chars.slice(0, index).join('')
      if (index === 0) {
        deleting = false
        typingTimer = setTimeout(step, 600)
        return
      }
      typingTimer = setTimeout(step, 90)
    }
  }

  typingTimer = setTimeout(step, 400)
}

onBeforeUnmount(() => {
  if (typingTimer) clearTimeout(typingTimer)
})

onMounted(() => {
  // Desktop, the installed app, "continue in browser" chosen before, or already installed: straight to sign-in.
  if (!shouldShowInstallPage()) {
    navigateTo('/auth/signin', { replace: true })
    return
  }
  ready.value = true
  startTyping()
})

async function onInstall() {
  if (!pwa.installEvent.value) {
    state.value = 'manual' // no prompt to show (iOS, or the browser has not offered one): explain the manual way
    return
  }
  busy.value = true
  try {
    const outcome = await pwa.install()
    if (outcome === 'accepted') {
      rememberInstalled()
      state.value = 'installed'
    }
    else if (outcome === 'dismissed') {
      state.value = 'declined'
    }
  }
  catch {
    state.value = 'manual'
  }
  finally {
    busy.value = false
  }
}

function continueInBrowser() {
  rememberBrowserChoice() // never show this page again on this browser
  pwa.dismissInstall() // and quiet the small install suggestion for a while too
  navigateTo('/auth/signin', { replace: true })
}
</script>

<style scoped>
.caret {
  display: inline-block;
  width: 4px;
  height: 0.85em;
  margin-inline-start: 6px;
  vertical-align: middle;
  background-color: #fdd00a;
  border-radius: 2px;
  animation: caret-blink 1s steps(1) infinite;
}

@keyframes caret-blink {
  0%, 50% { opacity: 1; }
  50.01%, 100% { opacity: 0; }
}
</style>
