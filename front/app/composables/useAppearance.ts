/**
 * User-customisable appearance: colour palette, sidebar style and content width.
 *
 * State lives in cookies (not localStorage) so the server renders the saved choice and there is no
 * flash on refresh. The palette is applied as `data-palette` on <html> (see app.vue); palettes only
 * re-tint surfaces (assets/css/palettes.css) -- the Polychem yellow #ffcc05 and IRANYekan are never touched.
 * Light / dark itself is handled by useThemeTransition (@nuxtjs/color-mode).
 */
export const PALETTES = [
  { id: 'default', label: 'پیش‌فرض', light: ['oklch(1 0 0)', 'oklch(0.97 0 0)'], dark: ['oklch(0 0 0)', 'oklch(0.2 0 0)'] },
  { id: 'brown', label: 'قهوه‌ای', light: ['oklch(0.985 0.008 55)', 'oklch(0.9 0.014 55)'], dark: ['oklch(0.17 0.02 55)', 'oklch(0.3 0.03 55)'] },
  { id: 'green', label: 'سبز', light: ['oklch(0.985 0.008 155)', 'oklch(0.9 0.014 155)'], dark: ['oklch(0.17 0.02 155)', 'oklch(0.3 0.03 155)'] },
  { id: 'blue', label: 'آبی', light: ['oklch(0.985 0.008 255)', 'oklch(0.9 0.014 255)'], dark: ['oklch(0.17 0.02 255)', 'oklch(0.3 0.03 255)'] },
  { id: 'purple', label: 'بنفش', light: ['oklch(0.985 0.008 305)', 'oklch(0.9 0.014 305)'], dark: ['oklch(0.17 0.02 305)', 'oklch(0.3 0.03 305)'] },
] as const

export const SIDEBAR_VARIANTS = [
  { id: 'sidebar', label: 'کلاسیک' },
  { id: 'floating', label: 'شناور' },
  { id: 'inset', label: 'داخل قاب' },
] as const

export const CONTENT_WIDTHS = [
  { id: 'fluid', label: 'تمام‌عرض' },
  { id: 'centered', label: 'مرکزی' },
] as const

export type PaletteId = typeof PALETTES[number]['id']
export type SidebarVariant = typeof SIDEBAR_VARIANTS[number]['id']
export type ContentWidth = typeof CONTENT_WIDTHS[number]['id']

const pick = <T extends string>(value: unknown, list: readonly { id: T }[], fallback: T): T =>
  list.some(i => i.id === value) ? value as T : fallback

export function useAppearance() {
  const opts = { maxAge: 60 * 60 * 24 * 365, path: '/', sameSite: 'lax' as const }
  const paletteCookie = useCookie<string | undefined>('pc_palette', opts)
  const sidebarCookie = useCookie<string | undefined>('pc_sidebar', opts)
  const widthCookie = useCookie<string | undefined>('pc_width', opts)

  // useState = one shared value for every component; first read seeds it from the cookie (SSR-safe).
  const palette = useState<PaletteId>('appearance:palette', () => pick(paletteCookie.value, PALETTES, 'default'))
  const sidebarVariant = useState<SidebarVariant>('appearance:sidebar', () => pick(sidebarCookie.value, SIDEBAR_VARIANTS, 'sidebar'))
  const contentWidth = useState<ContentWidth>('appearance:width', () => pick(widthCookie.value, CONTENT_WIDTHS, 'fluid'))

  const setPalette = (id: PaletteId, origin?: TransitionOrigin) => {
    if (palette.value === id) return
    runThemeTransition(async () => {
      palette.value = id
      paletteCookie.value = id
      // set it synchronously too: the view-transition snapshot must see the new palette
      document.documentElement.dataset.palette = id
      await nextTick()
    }, origin)
  }
  const setSidebarVariant = (id: SidebarVariant) => {
    sidebarVariant.value = id
    sidebarCookie.value = id
  }
  const setContentWidth = (id: ContentWidth) => {
    contentWidth.value = id
    widthCookie.value = id
  }
  const reset = (origin?: TransitionOrigin) => {
    setPalette('default', origin)
    setSidebarVariant('sidebar')
    setContentWidth('fluid')
  }

  return { palette, sidebarVariant, contentWidth, setPalette, setSidebarVariant, setContentWidth, reset }
}
