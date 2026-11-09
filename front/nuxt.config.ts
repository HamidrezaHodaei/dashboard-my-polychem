import tailwindcss from '@tailwindcss/vite'

// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
  // The whole app is an authenticated portal: the access token lives in browser memory and the
  // refresh cookie belongs to the API origin, so a server render can never know who the user is.
  // With SSR on, a hard reload ran the auth guard on the SERVER (no session yet) and redirected to
  // /auth/signin before the browser could restore the session -- the "reload logs me out" bug.
  ssr: false,
  future: {
    compatibilityVersion: 4,
  },
  modules: [
    '@nuxt/eslint',
    '@vueuse/nuxt',
    '@pinia/nuxt',
    'shadcn-nuxt',
    '@nuxtjs/color-mode',
    '@nuxt/icon',
    '@nuxtjs/google-fonts',
  ],
  // Shown while the SPA boots / restores the session, so the user never stares at a black page.
  spaLoadingTemplate: true,
  app: {
    pageTransition: false,
    layoutTransition: false,
    head: {
      titleTemplate: `%s %separator %siteName`,
      htmlAttrs: {
        lang: 'fa',
        dir: 'rtl',
      },
      templateParams: {
        separator: '|',
        siteName: process.env.NUXT_PUBLIC_SITE_NAME || 'پلیکم',
      },
    },
  },
  runtimeConfig: {
    public: {
      siteName: 'پلیکم من',
      siteUrl: 'https://myportal.polychemmb.com',
      // Phase 5: single centralized base URL for the Flask backend --
      // repoint via NUXT_PUBLIC_API_BASE for staging/production without
      // touching app code (app/services/backendApi.ts).
      //
      // Dev prefix is `/backend`, NOT `/api`: @nuxt/icon registers its own
      // Nitro server route at `/api/_nuxt_icon/*`, and devProxy matches by
      // path prefix, so a `/api` proxy rule silently swallowed those
      // requests too and forwarded them to Flask (which 404s on a path it
      // never defined) -- that's what broke icon loading in dev. Flask's
      // own routes are unaffected; only how the Nuxt dev server reaches
      // them changes.
      apiBase: process.env.NUXT_PUBLIC_API_BASE || (import.meta.dev ? '/backend' : 'https://apimy.polychemmb.com/api'),
    },
  },
  // In dev the app calls the same-origin `/backend`; forward it to the
  // Flask backend's `/api` (override with NUXT_DEV_API_PROXY). Keeps
  // cookies same-site and avoids CORS in development. Must NOT be `/api`
  // -- see the apiBase comment above.
  nitro: {
    devProxy: {
      '/backend': {
        target: process.env.NUXT_DEV_API_PROXY || 'https://apimy.polychemmb.com/api',
        changeOrigin: true,
        // The API scopes the refresh cookie to Path=/api/auth, but in dev the browser calls
        // /backend/auth/refresh -- so the cookie was never sent and every reload logged out.
        cookiePathRewrite: { '/api/auth': '/backend/auth', '/api': '/backend' },
        cookieDomainRewrite: '',
      },
    },
  },
  css: ['~/assets/css/main.css'],
  shadcn: {
    prefix: '',
    componentDir: './app/components/ui',
  },
  colorMode: {
    preference: 'system',
    classSuffix: '',
    disableTransition: true,
  },
  icon: {
    serverBundle: {
      collections: ['lucide'],
    },
    clientBundle: {
      icons: ['logos:google-icon'],
    },
  },
  googleFonts: {
    families: {
      Vazirmatn: [400, 500, 600, 700],
    },
    display: 'swap',
    download: true,
  },
  components: {
    dirs: [
      {
        path: '~/components',
        ignore: ['**/*.ts'],
      },
    ],
  },
  vite: {
    plugins: [
      tailwindcss(),
    ],
  },
  eslint: {
    config: {
      stylistic: true,
    },
  },
  compatibilityDate: '2025-07-23',
  devtools: {
    enabled: true,
  },
})
